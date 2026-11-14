import argparse
import json
from pathlib import Path
from .baseline import HistogramModel


def main():
    parser = argparse.ArgumentParser(description="Simulation-only full1C–8C reference; not an identity tool")
    parser.add_argument("--cm", type=float, required=True)
    parser.add_argument("--ibd1-segments", type=int, required=True)
    parser.add_argument("--method", choices=["cm_unconditional", "cm_segments_unconditional", "cm_positive_only", "cm_segments_positive_only"], default="cm_segments_positive_only")
    args = parser.parse_args()
    if "positive_only" in args.method and args.cm <= 0:
        parser.error("Positive-sharing method cannot classify a zero-sharing observation")
    saved = json.loads((Path(__file__).parent / "results/models.json").read_text())
    result = HistogramModel.from_dict(saved["models"][args.method]).predict(args.cm, args.ibd1_segments)
    print(json.dumps({"method": args.method, **result}, indent=2))


if __name__ == "__main__":
    main()
