import argparse
from cns_multimodalai.inference.predict_from_rna import run_rna_inference

def main():
    parser = argparse.ArgumentParser(description="Run CNS-MultiModalAI RNA inference.")
    parser.add_argument("--expression_csv", required=True, help="External expression CSV")
    parser.add_argument("--output_dir", required=True, help="Output folder")
    parser.add_argument("--no_canvas", action="store_true", help="Disable morphology canvas generation")
    parser.add_argument("--max_cases", type=int, default=None, help="Optional limit for quick demo")
    args = parser.parse_args()

    result = run_rna_inference(
        expression_csv=args.expression_csv,
        output_dir=args.output_dir,
        make_morphology_canvas=not args.no_canvas,
        max_cases=args.max_cases,
    )
    print(result)

if __name__ == "__main__":
    main()
