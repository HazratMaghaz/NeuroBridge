"""Unit tests for CLI configuration, data-contract checks and safe stage behavior."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from neurobridge.cli import load_config, validate_inputs, execute


class CliValidationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "study").mkdir()
        self.project = self.root / "study"
        self.config_path = self.root / "config.yaml"

    def config(self, **kw):
        conf = {"project": "study", "run_id": "my_run", "device": "cpu", "enrichment": "programs_only"}
        conf.update(kw)
        import yaml
        self.config_path.write_text(yaml.safe_dump(conf))
        return load_config(self.config_path)

    def make_inputs(self):
        n=686
        ids=[f"TOY{i:04d}" for i in range(n)]
        labels=["TCGA-GBM"]*195+["TCGA-LGG"]*491
        splits=["train"]*480+["val"]*103+["test"]*103
        for rel in ["metadata", "data/expression/processed", "features/ctranspath_7B_wsi_streaming_full", "embeddings/slide_embeddings"]:
            (self.project / rel).mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"patient_id":ids,"split":splits,"project_id":labels}).to_csv(self.project/"metadata/phase6b_patient_splits.csv",index=False)
        expr=pd.DataFrame(np.zeros((n,11),dtype="float32"),columns=[f"ENSG{i:011d}" for i in range(11)])
        expr.insert(0,"patient_id",ids)
        expr.to_csv(self.project/"data/expression/processed/expression_matrix_log2_tpm_filtered.csv",index=False)
        pd.DataFrame({"gene_id_clean":[f"ENSG{i:011d}" for i in range(11)],"gene_type":["protein_coding"]*11}).to_csv(self.project/"data/expression/processed/expression_gene_annotation.csv",index=False)
        for path, dim, prefix in [("features/ctranspath_7B_wsi_streaming_full/patient_level_ctranspath_mean_embeddings.csv",768,"ctranspath_feat_"),("embeddings/slide_embeddings/resnet50_full_selected_best_mean_pool_patient_embeddings_final.csv",2048,"resnet50_feat_")]:
            with (self.project/path).open("w") as f:
                f.write("patient_id,"+",".join(f"{prefix}{i}" for i in range(dim))+"\n")
                for pid in ids:
                    f.write(pid+","+",".join("0" for _ in range(dim))+"\n")

    def test_config_relative_project(self):
        c=self.config()
        self.assertEqual(c.project, self.project)
        self.assertEqual(c.run_id,"my_run")

    def test_config_rejects_unknown_key(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            self.config(custom_secret="not-supported")

    def test_run_id_rejects_traversal(self):
        with self.assertRaisesRegex(ValueError, "run_id"):
            self.config(run_id="../../outside")

    def test_configuration_rejects_missing_gmt(self):
        with self.assertRaisesRegex(ValueError, "GMT"):
            self.config(enrichment="not-present.gmt")

    def test_missing_file_shows_error(self):
        with self.assertRaisesRegex(ValueError,"Missing"):
            validate_inputs(self.config(),"classification")

    def test_canonical_patient_contract(self):
        self.make_inputs()
        messages=validate_inputs(self.config(),"classification")
        self.assertTrue(any("686 patients" in m for m in messages))
        messages=validate_inputs(self.config(),"biology")
        self.assertTrue(any("CTransPath" in m for m in messages))

    def test_biology_stage_does_not_require_resnet(self):
        self.make_inputs()
        (self.project / "embeddings/slide_embeddings/resnet50_full_selected_best_mean_pool_patient_embeddings_final.csv").unlink()
        msgs = validate_inputs(self.config(), "biology")
        self.assertTrue(any("CTransPath" in x for x in msgs))
        with self.assertRaisesRegex(ValueError, "Missing resnet"):
            validate_inputs(self.config(), "classification")

    def test_rejects_duplicate_patients(self):
        self.make_inputs()
        p=self.project/"metadata/phase6b_patient_splits.csv"
        data=pd.read_csv(p);data.loc[1,"patient_id"]=data.loc[0,"patient_id"];data.to_csv(p,index=False)
        with self.assertRaisesRegex(ValueError,"duplicate"):
            validate_inputs(self.config(),"classification")

    def test_rejects_existing_output(self):
        self.make_inputs()
        folder=self.project/"results/corrected_v3/my_run/classification"
        folder.mkdir(parents=True)
        (folder/"results.csv").write_text("keep me")
        with self.assertRaisesRegex(ValueError,"Output exists"):
            validate_inputs(self.config(),"classification")
        self.assertEqual((folder/"results.csv").read_text(),"keep me")

    def test_classification_dry_run_does_not_train(self):
        self.make_inputs()
        with patch("neurobridge.cli._run", side_effect=AssertionError("Training called")):
            execute(self.config(),"classification",dry_run=True)


if __name__ == "__main__":
    unittest.main()
