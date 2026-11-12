"""CLI for the corrected, retrospective NeuroBridge research analyses.

Never trains, edits inputs, or downloads data during validation. Model-fitting
scripts in analysis/scripts are invoked unmodified via subprocess.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis" / "scripts"

# The release is intentionally tied to the canonical TCGA-GBM/LGG patient split.
INPUTS = {
    "splits": "metadata/phase6b_patient_splits.csv",
    "expression": "data/expression/processed/expression_matrix_log2_tpm_filtered.csv",
    "annotation": "data/expression/processed/expression_gene_annotation.csv",
    "ctranspath": "features/ctranspath_7B_wsi_streaming_full/patient_level_ctranspath_mean_embeddings.csv",
    "resnet": "embeddings/slide_embeddings/resnet50_full_selected_best_mean_pool_patient_embeddings_final.csv",
    "rna_external": "results/external_validation/phase12a_v2_cptac_rna_harmonization/phase12a_v2_cptac_rna_harmonization_strategy_comparison.csv",
    "wsi_external": "results/external_validation/phase12d_final_consolidation/phase12d_final_external_validation_summary_table.csv",
    "loo": "results/genemorph_loo_rerun_20260818_final/loo_query_level_results.csv",
    "loo_assertions": "results/genemorph_loo_rerun_20260818_final/self_exclusion_assertion_report.txt",
}
STAGES = {"classification", "biology", "external", "package", "core", "full"}
ALLOWED_KEYS = {"project", "run_id", "split_csv", "device", "cv_folds", "cv_repeats", "epochs", "patience", "pca_dim", "topvar", "img_to_mol", "enrichment"}


@dataclass(frozen=True)
class Config:
    project: Path
    run_id: str
    split_csv: Path
    device: str
    cv_folds: int
    cv_repeats: int
    epochs: int
    patience: int
    pca_dim: int
    topvar: int
    img_to_mol: str
    enrichment: str


def _positive(name: str, val: Any, minimum: int = 1) -> int:
    if type(val) is not int or val < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return val


def load_config(filename: str | Path) -> Config:
    path = Path(filename).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Configuration not found: {path}")
    with path.open(encoding="utf-8") as handle:
        settings = yaml.safe_load(handle)
    if not isinstance(settings, dict):
        raise ValueError("Configuration must be a YAML mapping")
    unknown = settings.keys() - ALLOWED_KEYS
    if unknown:
        raise ValueError(f"Unknown configuration keys: {sorted(unknown)}")
    if not isinstance(settings.get("project"), str) or not settings["project"].strip():
        raise ValueError("project must be a non-empty directory path")
    project = Path(settings["project"]).expanduser()
    if not project.is_absolute():
        project = path.parent / project
    project = project.resolve()
    if not project.is_dir():
        raise ValueError(f"Study directory does not exist: {project}")
    run_id = settings.get("run_id", "reproduction")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", run_id) or run_id in {".", ".."}:
        raise ValueError("run_id must be 1–80 filename-safe characters; no slashes or traversal")
    split_csv = settings.get("split_csv", INPUTS["splits"])
    if not isinstance(split_csv, str) or not split_csv.strip():
        raise ValueError("split_csv must be a non-empty path")
    split_csv = Path(split_csv).expanduser()
    if not split_csv.is_absolute():
        split_csv = project / split_csv
    split_csv = split_csv.resolve()
    device = settings.get("device", "cpu")
    if device not in {"cpu", "cuda"}:
        raise ValueError("device must be cpu or cuda")
    mapper = settings.get("img_to_mol", "ridge")
    if mapper not in {"ridge", "mlp"}:
        raise ValueError("img_to_mol must be ridge or mlp")
    enrichment = settings.get("enrichment", "programs_only")
    if not isinstance(enrichment, str) or not enrichment.strip():
        raise ValueError("enrichment must be programs_only, enrichr, or a .gmt path")
    if enrichment not in {"programs_only", "enrichr"}:
        gmt = Path(enrichment).expanduser()
        if not gmt.is_absolute():
            gmt = path.parent / gmt
        gmt = gmt.resolve()
        if gmt.suffix.lower() != ".gmt" or not gmt.is_file():
            raise ValueError(f"Enrichment GMT file missing or not .gmt: {gmt}")
        enrichment = str(gmt)
    return Config(project, run_id, split_csv, device,
        _positive("cv_folds", settings.get("cv_folds", 5), 2),
        _positive("cv_repeats", settings.get("cv_repeats", 3)),
        _positive("epochs", settings.get("epochs", 150)),
        _positive("patience", settings.get("patience", 20)),
        _positive("pca_dim", settings.get("pca_dim", 128), 2),
        _positive("topvar", settings.get("topvar", 5000), 2), mapper, enrichment)


def _read_ids(path: Path, label: str) -> pd.DataFrame:
    columns = pd.read_csv(path, nrows=0).columns
    if "patient_id" not in columns:
        raise ValueError(f"{label}: missing patient_id column")
    selected = [c for c in ("patient_id", "split", "project_id") if c in columns]
    frame = pd.read_csv(path, dtype={"patient_id": "string"}, usecols=selected)
    frame["patient_id"] = frame["patient_id"].str.strip()
    if frame.patient_id.isna().any() or frame.patient_id.eq("").any():
        raise ValueError(f"{label}: missing/empty patient IDs")
    if frame.patient_id.duplicated().any():
        raise ValueError(f"{label}: duplicate patient IDs")
    return frame


def _ordered_columns(path: Path, patterns: list[str], dimension: int, label: str) -> None:
    import re
    cols = pd.read_csv(path, nrows=0).columns
    for pattern in patterns:
        idx = []
        for col in cols:
            match = re.fullmatch(pattern, col)
            if match:
                idx.append(int(match.group(1)))
        if len(idx) == dimension and sorted(idx) == list(range(dimension)):
            return
    raise ValueError(f"{label}: expected {dimension} uniquely indexed feature columns 0..{dimension - 1}")


def validate_inputs(config: Config, stage: str) -> list[str]:
    """Read-only preflight. Never uses held-out data to fit transformations."""
    if stage not in STAGES:
        raise ValueError(f"Unsupported stage: {stage}")
    messages: list[str] = []
    if stage in {"classification", "biology", "core", "full"}:
        needed = {"expression", "ctranspath"}
        if stage in {"classification", "core", "full"}:
            needed.add("resnet")
        paths = {k: config.project / v for k, v in INPUTS.items() if k in needed}
        paths["splits"] = config.split_csv
        if stage in {"biology", "core", "full"}:
            paths["annotation"] = config.project / INPUTS["annotation"]
        for name, file in paths.items():
            if not file.is_file():
                raise ValueError(f"Missing {name} input: {file}")
        split = _read_ids(paths["splits"], "splits")
        exp = _read_ids(paths["expression"], "expression")
        img = _read_ids(paths["ctranspath"], "ctranspath")
        res = _read_ids(paths["resnet"], "resnet") if "resnet" in paths else None
        if not {"split", "project_id"} <= set(split.columns):
            raise ValueError("Split manifest requires split and project_id columns")
        if len(split) != 686 or split["split"].value_counts().to_dict() != {"train": 480, "val": 103, "test": 103}:
            raise ValueError("Canonical cohort must contain 686 patients, split 480/103/103")
        if split["project_id"].value_counts().to_dict() != {"TCGA-LGG": 491, "TCGA-GBM": 195}:
            raise ValueError("Canonical project labels must contain 491 LGG and 195 GBM patients")
        reference = set(split.patient_id)
        frames = [("expression", exp), ("ctranspath", img)]
        if res is not None:
            frames.append(("resnet", res))
        for name, frame in frames:
            if len(frame) != 686 or set(frame.patient_id) != reference:
                raise ValueError(f"{name}: mismatched patient IDs; no silent inner joins")
        if "project_id" in exp:
            paired = split[["patient_id", "project_id"]].merge(exp[["patient_id", "project_id"]], on="patient_id", suffixes=("_split", "_expression"), validate="one_to_one")
            if not paired.project_id_split.equals(paired.project_id_expression):
                raise ValueError("Expression and canonical split project_id labels disagree")
        expr_headers = pd.read_csv(paths["expression"], nrows=0).columns
        if sum(bool(re.fullmatch(r"ENSG\d+(?:\.\d+)?", col)) for col in expr_headers) < 10:
            raise ValueError("Expression matrix needs numeric ENSG-style gene columns; check headers")
        _ordered_columns(paths["ctranspath"], [r"ctranspath_feat_(\d+)", r"ctranspath_(\d+)", r"img_feat_(\d+)"], 768, "CTransPath")
        if res is not None:
            _ordered_columns(paths["resnet"], [r"img_feat_(\d+)", r"resnet50_mean_(\d+)", r"resnet50_feat_(\d+)"], 2048, "ResNet50")
        if stage in {"biology", "core", "full"}:
            anno_headers = set(pd.read_csv(paths["annotation"], nrows=0).columns)
            if not {"gene_id_clean", "gene_type"} <= anno_headers:
                raise ValueError("Annotation requires gene_id_clean and gene_type")
        messages.append("Canonical cohort: 686 patients (195 GBM, 491 LGG); partitions 480/103/103")
        messages.append("Expression and CTransPath (768)" + (" and ResNet50 (2048)" if res is not None else "") + ": patient matching and column headers OK")
        messages.append("Note: finite numeric data and feature-value integrity are checked again during analysis")
    if stage in {"external", "full"}:
        for key in ("rna_external", "wsi_external", "loo", "loo_assertions"):
            src = config.project / INPUTS[key]
            if not src.is_file():
                raise ValueError(f"Historical {key} output required for external reporting: {src}")
        messages.append("Historical CPTAC/Gene2Morph source files exist; values checked during reporting")
    if stage == "package":
        expected = config.project / "results" / "corrected_v3" / config.run_id
        for file in ["classification/manifest.json", "biology/manifest.json", "external_and_retrieval/manifest.json"]:
            if not (expected / file).is_file():
                raise ValueError(f"Packaging requires previous stage output: {expected / file}")
    output = config.project / "results" / "corrected_v3" / config.run_id
    stages = {"classification": ("classification",), "biology": ("biology",), "external": ("external_and_retrieval",),
              "package": (), "core": ("classification", "biology"),
              "full": ("classification", "biology", "external_and_retrieval")}[stage]
    for sub in stages:
        target = output / sub
        if target.exists() and any(target.iterdir()):
            raise ValueError(f"Output exists; choose a new run_id to avoid overwriting: {target}")
    messages.append(f"Outputs: {output}")
    return messages


def _run(cmd: list[str], env: dict[str, str]) -> None:
    print("Executing:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=env, cwd=str(ROOT))


def execute(config: Config, stage: str, dry_run: bool = False) -> None:
    msgs = validate_inputs(config, stage)
    for item in msgs:
        print("CHECK:", item)
    if dry_run:
        print("DRY RUN: No model training performed")
        return
    if stage in {"classification", "core", "full"}:
        try:
            import torch
        except ImportError as exc:
            raise ValueError("PyTorch missing. Install CPU torch from the official PyTorch wheel index, or install a supported CUDA build") from exc
        if config.device == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA requested but PyTorch reports it unavailable; select device: cpu or fix your PyTorch install")
    env = os.environ.copy()
    env["NEUROBRIDGE_SPLITS_CSV"] = str(config.split_csv)
    common = ["--project", str(config.project), "--run-id", config.run_id]
    if stage in {"classification", "core", "full"}:
        _run([sys.executable, str(ANALYSIS / "01_corrected_classification.py"), *common,
            "--cv-folds", str(config.cv_folds), "--cv-repeats", str(config.cv_repeats),
            "--epochs", str(config.epochs), "--patience", str(config.patience),
            "--pca-dim", str(config.pca_dim), "--topvar", str(config.topvar),
            "--img-to-mol", config.img_to_mol, "--device", config.device], env)
    if stage in {"biology", "core", "full"}:
        enrich = (["--enrichr"] if config.enrichment == "enrichr" else
                  [] if config.enrichment == "programs_only" else ["--gmt", config.enrichment])
        _run([sys.executable, str(ANALYSIS / "02_corrected_biology.py"), *common, *enrich], env)
    if stage in {"external", "full"}:
        _run([sys.executable, str(ANALYSIS / "03_external_genemorph_reporting.py"), *common], env)
    if stage in {"package", "full"}:
        _run([sys.executable, str(ANALYSIS / "04_verify_and_package.py"), *common], env)
    print(f"SUCCESS: {stage} outputs at {config.project / 'results' / 'corrected_v3' / config.run_id}")


def demo(destination: str | None) -> None:
    try:
        import torch  # noqa: F401; required only when executing demo or classification
    except ImportError as exc:
        raise ValueError("PyTorch is required for demo: install the CPU build using the official PyTorch wheel index") from exc
    if destination:
        root = Path(destination).expanduser().resolve()
        if root.exists() and any(root.iterdir()):
            raise ValueError(f"Demo output directory not empty: {root}")
        root.mkdir(parents=True, exist_ok=True)
    else:
        root = Path(tempfile.mkdtemp(prefix="neurobridge-demo-"))
    env = os.environ.copy()
    env.update({"OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2"})
    _run([sys.executable, str(ROOT / "analysis/tests/create_synthetic_dataset.py"), "--out", str(root)], env)
    _run([sys.executable, str(ANALYSIS / "01_corrected_classification.py"),
          "--project", str(root), "--run-id", "synthetic_smoke", "--cv-folds", "2", "--cv-repeats", "1",
          "--epochs", "1", "--patience", "1", "--pca-dim", "16", "--topvar", "100",
          "--img-to-mol", "ridge", "--device", "cpu", "--demo", "--skip-resnet"], env)
    print(f"SYNTHETIC SMOKE TEST PASSED (not manuscript results): {root}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="neurobridge", description="Retrospective multimodal glioma research CLI (not diagnostic)")
    sub = parser.add_subparsers(dest="command", required=True)
    p_demo = sub.add_parser("demo", help="Run synthetic 320-patient CPU smoke test (requires torch)")
    p_demo.add_argument("--output", help="Optional directory for synthetic outputs")
    p_val = sub.add_parser("validate", help="Check input paths, canonical patient splits and feature dimensions")
    p_val.add_argument("--config", required=True)
    p_val.add_argument("--stage", choices=sorted(STAGES), default="classification")
    p_run = sub.add_parser("run", help="Run corrected scientific stages on prepared features")
    p_run.add_argument("--config", required=True)
    p_run.add_argument("--stage", choices=sorted(STAGES), default="core")
    p_run.add_argument("--dry-run", action="store_true", help="Validate without training")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            demo(args.output)
        elif args.command == "validate":
            config = load_config(args.config)
            for message in validate_inputs(config, args.stage):
                print("CHECK:", message)
            print("VALIDATION PASSED (headers and patient sets; not a numerical-data audit)")
        else:
            execute(load_config(args.config), args.stage, dry_run=args.dry_run)
        return 0
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError, yaml.YAMLError) as exc:
        print(f"NeuroBridge error: {exc}", file=sys.stderr)
        return 2
