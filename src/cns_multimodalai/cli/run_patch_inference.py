import argparse
from pathlib import Path
import pandas as pd

from cns_multimodalai.inference.predict_from_patches import predict_from_patch_folder
from cns_multimodalai.inference.generate_report import generate_markdown_report
from cns_multimodalai import config

def main():
    parser = argparse.ArgumentParser(description="Run CNS-MultiModalAI patch-folder inference.")
    parser.add_argument("--patch_dir", required=True, help="Folder with patch images")
    parser.add_argument("--output_dir", required=True, help="Output folder")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result, emb, clf_pack = predict_from_patch_folder(args.patch_dir, output_dir=output_dir)
    pred_df = pd.DataFrame([result])

    report_path = output_dir / "patch_inference_report.md"
    generate_markdown_report(
        title="CNS-MultiModalAI Patch Inference Report",
        prediction_df=pred_df,
        output_path=report_path,
        extra_notes=[config.MODEL_SCOPE_NOTE],
    )

    print(result)
    print("Report:", report_path)

if __name__ == "__main__":
    main()
