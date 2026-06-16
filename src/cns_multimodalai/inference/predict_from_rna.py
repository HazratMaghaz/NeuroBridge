# CNS JSON safety patch: prevents ndarray JSON serialization failures
from cns_multimodalai.inference.json_safety import patch_json_encoder
patch_json_encoder()

from pathlib import Path
import pandas as pd

from cns_multimodalai import config
from cns_multimodalai.io_utils import ensure_dir, write_json
from cns_multimodalai.preprocessing.harmonize_expression import (
    predict_rna_gbm_like,
    train_molecular_to_image_model,
    predict_image_embedding_from_rna,
)
from cns_multimodalai.inference.retrieve_morphology_canvas import (
    retrieve_real_patches_from_predicted_image_embedding,
    make_canvas,
)
from cns_multimodalai.inference.generate_report import generate_markdown_report

def run_rna_inference(
    expression_csv,
    output_dir=None,
    make_morphology_canvas=True,
    strategy="log2_fpkm_uq_plus1",
    max_cases=None,
):
    expression_csv = Path(expression_csv)

    if output_dir is None:
        output_dir = config.INFERENCE_OUT_ROOT / f"rna_{expression_csv.stem}"
    output_dir = ensure_dir(output_dir)

    pred_df, data, classifier = predict_rna_gbm_like(expression_csv, strategy=strategy)

    if max_cases is not None:
        pred_df = pred_df.head(max_cases).copy()

    pred_path = output_dir / "rna_gbm_lgg_like_predictions.csv"
    pred_df.to_csv(pred_path, index=False)

    result = {
        "input_csv": str(expression_csv),
        "output_dir": str(output_dir),
        "n_cases": int(len(pred_df)),
        "strategy": strategy,
        "predictions_csv": str(pred_path),
        "model_scope_note": config.MODEL_SCOPE_NOTE,
    }

    canvas_index_rows = []

    if make_morphology_canvas:
        mol2img = train_molecular_to_image_model(data)
        pred_img = predict_image_embedding_from_rna(data, mol2img)

        patient_to_idx = {pid: i for i, pid in enumerate(data["external_patient_ids"])}
        for pid in pred_df["patient_id"].tolist():
            idx = patient_to_idx[pid]
            patch_paths, retrieval_df = retrieve_real_patches_from_predicted_image_embedding(pred_img[idx])

            case_dir = ensure_dir(output_dir / "morphology_canvas" / str(pid))
            canvas_path = case_dir / f"{pid}_real_patch_morphology_canvas.jpg"
            make_canvas(patch_paths, canvas_path)

            retrieval_path = case_dir / f"{pid}_retrieved_patch_index.csv"
            retrieval_df.to_csv(retrieval_path, index=False)

            canvas_index_rows.append({
                "patient_id": pid,
                "canvas_path": str(canvas_path),
                "retrieval_csv": str(retrieval_path),
                "note": config.MORPHOLOGY_NOTE,
            })

        canvas_index = pd.DataFrame(canvas_index_rows)
        canvas_index_path = output_dir / "rna_to_morphology_canvas_index.csv"
        canvas_index.to_csv(canvas_index_path, index=False)
        result["canvas_index_csv"] = str(canvas_index_path)

    # Always generate and return embedding if not making canvas
    if "pred_img" not in locals():
        mol2img = train_molecular_to_image_model(data)
        pred_img = predict_image_embedding_from_rna(data, mol2img)

    # Save patient embeddings to a dict
    result["_predicted_image_embeddings"] = {}
    patient_to_idx = {pid: i for i, pid in enumerate(data["external_patient_ids"])}
    for pid in pred_df["patient_id"].tolist():
        idx = patient_to_idx[pid]
        result["_predicted_image_embeddings"][pid] = pred_img[idx]

    report_path = output_dir / "rna_inference_report.md"
    generate_markdown_report(
        title="CNS-MultiModalAI RNA Inference Report",
        prediction_df=pred_df,
        output_path=report_path,
        extra_notes=[
            config.MODEL_SCOPE_NOTE,
            config.MORPHOLOGY_NOTE if make_morphology_canvas else "",
        ],
    )
    result["report_md"] = str(report_path)

    write_json(result, output_dir / "rna_inference_run_summary.json")
    return result
