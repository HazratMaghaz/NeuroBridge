from pathlib import Path

def generate_markdown_report(title, prediction_df, output_path, extra_notes=None):
    if extra_notes is None:
        extra_notes = []

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("## Prediction summary")
    lines.append("")
    lines.append(f"Number of cases: {len(prediction_df)}")
    lines.append("")

    if "predicted_class" in prediction_df.columns:
        vc = prediction_df["predicted_class"].value_counts().to_dict()
        lines.append("### Predicted class counts")
        lines.append("")
        for k, v in vc.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    show_cols = [c for c in ["patient_id", "prob_GBM_like", "predicted_class", "n_patches"] if c in prediction_df.columns]
    if show_cols:
        lines.append("### First predictions")
        lines.append("")
        lines.append(prediction_df[show_cols].head(20).to_markdown(index=False))
        lines.append("")

    notes = [n for n in extra_notes if n]
    if notes:
        lines.append("## Important notes")
        lines.append("")
        for n in notes:
            lines.append(f"- {n}")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
