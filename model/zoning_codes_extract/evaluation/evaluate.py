"""
Evaluation script for the end-to-end zoning code extraction pipeline.

Evaluates the full 3-stage pipeline (Extractor -> Validator -> Categorizer)
against ground truth zone codes from zoneomics CSVs.
"""

import json
import csv
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Tuple
from collections import defaultdict

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from zoning_extract import (
    ZoningCodePipeline,
    CityMatcher,
    load_zoneomics_csv,
    normalize_zone_code
)


@dataclass
class EvaluationMetrics:
    """Metrics for a single city."""
    city: str
    state: str
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float
    recall: float
    f1: float
    ground_truth_codes: List[str]
    predicted_codes: List[str]
    matched_codes: List[str]
    missed_codes: List[str]
    extra_codes: List[str]


class PipelineEvaluator:
    """
    Evaluates the end-to-end zoning code extraction pipeline.

    Compares extracted zone codes against ground truth from zoneomics CSVs.
    Computes precision, recall, and F1 metrics.
    """

    def __init__(
        self,
        pipeline: ZoningCodePipeline,
        zoneomics_dir: str = "data/zoneomics",
        municode_dir: str = "tmp/zoning_ordinance"
    ):
        """
        Initialize evaluator.

        Args:
            pipeline: Trained pipeline to evaluate
            zoneomics_dir: Directory with ground truth CSVs
            municode_dir: Directory with ordinances
        """
        self.pipeline = pipeline
        self.zoneomics_dir = Path(zoneomics_dir)
        self.municode_dir = Path(municode_dir)

        # Initialize city matcher
        self.city_matcher = CityMatcher(
            str(self.zoneomics_dir),
            str(self.municode_dir)
        )

    def evaluate_city(
        self,
        state: str,
        city: str
    ) -> EvaluationMetrics:
        """
        Evaluate pipeline on a single city.

        Args:
            state: State name or abbreviation
            city: City name

        Returns:
            EvaluationMetrics for the city
        """
        # Load ground truth
        match = self.city_matcher.get_match(state, city)
        if not match:
            raise ValueError(f"No match found for {city}, {state}")

        ground_truth = load_zoneomics_csv(match.zoneomics_csv)
        ground_truth_codes = {normalize_zone_code(d.code) for d in ground_truth}

        # Run pipeline
        try:
            predictions = self.pipeline.extract_from_ordinances(
                match.municode_folder,
                zoning_only=True
            )
            predicted_codes = {normalize_zone_code(z.zone_code) for z in predictions}
        except Exception as e:
            print(f"Error running pipeline on {city}, {state}: {e}")
            predicted_codes = set()

        # Compute metrics
        tp_codes = ground_truth_codes & predicted_codes
        fp_codes = predicted_codes - ground_truth_codes
        fn_codes = ground_truth_codes - predicted_codes

        tp = len(tp_codes)
        fp = len(fp_codes)
        fn = len(fn_codes)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return EvaluationMetrics(
            city=city,
            state=state,
            true_positive=tp,
            false_positive=fp,
            false_negative=fn,
            precision=precision,
            recall=recall,
            f1=f1,
            ground_truth_codes=sorted(ground_truth_codes),
            predicted_codes=sorted(predicted_codes),
            matched_codes=sorted(tp_codes),
            missed_codes=sorted(fn_codes),
            extra_codes=sorted(fp_codes)
        )

    def evaluate_test_set(
        self,
        test_cities: List[Tuple[str, str]],
        output_dir: str = "model/zoning_codes_extract/evaluation/results"
    ) -> Dict:
        """
        Evaluate pipeline on test set.

        Args:
            test_cities: List of (state, city) tuples
            output_dir: Where to save results

        Returns:
            Dictionary with aggregated metrics
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        all_metrics = []

        print(f"Evaluating {len(test_cities)} test cities...")

        for i, (state, city) in enumerate(test_cities):
            print(f"\n[{i+1}/{len(test_cities)}] Evaluating {city}, {state}")

            try:
                metrics = self.evaluate_city(state, city)
                all_metrics.append(metrics)

                print(f"  Precision: {metrics.precision:.3f}")
                print(f"  Recall: {metrics.recall:.3f}")
                print(f"  F1: {metrics.f1:.3f}")
                print(f"  TP: {metrics.true_positive}, FP: {metrics.false_positive}, FN: {metrics.false_negative}")

            except Exception as e:
                print(f"  Error: {e}")
                continue

        # Compute aggregate metrics
        aggregate = self._compute_aggregate_metrics(all_metrics)

        # Save results
        self._save_results(all_metrics, aggregate, output_path)

        return aggregate

    def _compute_aggregate_metrics(
        self,
        all_metrics: List[EvaluationMetrics]
    ) -> Dict:
        """
        Compute aggregate metrics across all cities.

        Args:
            all_metrics: Metrics for each city

        Returns:
            Dictionary with aggregate metrics
        """
        if not all_metrics:
            return {}

        # Micro-averaged metrics (aggregate TP/FP/FN across all cities)
        total_tp = sum(m.true_positive for m in all_metrics)
        total_fp = sum(m.false_positive for m in all_metrics)
        total_fn = sum(m.false_negative for m in all_metrics)

        micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        micro_f1 = 2 * micro_precision * micro_recall / (micro_precision + micro_recall) \
            if (micro_precision + micro_recall) > 0 else 0.0

        # Macro-averaged metrics (average across cities)
        macro_precision = sum(m.precision for m in all_metrics) / len(all_metrics)
        macro_recall = sum(m.recall for m in all_metrics) / len(all_metrics)
        macro_f1 = sum(m.f1 for m in all_metrics) / len(all_metrics)

        return {
            "num_cities": len(all_metrics),
            "total_true_positive": total_tp,
            "total_false_positive": total_fp,
            "total_false_negative": total_fn,
            "micro_precision": micro_precision,
            "micro_recall": micro_recall,
            "micro_f1": micro_f1,
            "macro_precision": macro_precision,
            "macro_recall": macro_recall,
            "macro_f1": macro_f1,
        }

    def _save_results(
        self,
        all_metrics: List[EvaluationMetrics],
        aggregate: Dict,
        output_path: Path
    ):
        """Save evaluation results to files."""
        # Save per-city metrics
        per_city_file = output_path / "per_city_metrics.json"
        with open(per_city_file, 'w') as f:
            json.dump([asdict(m) for m in all_metrics], f, indent=2)
        print(f"\nSaved per-city metrics to {per_city_file}")

        # Save aggregate metrics
        aggregate_file = output_path / "aggregate_metrics.json"
        with open(aggregate_file, 'w') as f:
            json.dump(aggregate, f, indent=2)
        print(f"Saved aggregate metrics to {aggregate_file}")

        # Save summary CSV
        summary_file = output_path / "summary.csv"
        with open(summary_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'city', 'state', 'precision', 'recall', 'f1',
                'true_positive', 'false_positive', 'false_negative'
            ])
            writer.writeheader()
            for m in all_metrics:
                writer.writerow({
                    'city': m.city,
                    'state': m.state,
                    'precision': f"{m.precision:.3f}",
                    'recall': f"{m.recall:.3f}",
                    'f1': f"{m.f1:.3f}",
                    'true_positive': m.true_positive,
                    'false_positive': m.false_positive,
                    'false_negative': m.false_negative
                })
        print(f"Saved summary CSV to {summary_file}")


def load_test_cities(data_dir: str = "model/zoning_codes_extract/training/data") -> List[Tuple[str, str]]:
    """
    Load test cities from test split.

    Args:
        data_dir: Directory with training data splits

    Returns:
        List of (state, city) tuples
    """
    test_file = Path(data_dir) / "test.jsonl"

    if not test_file.exists():
        raise FileNotFoundError(f"Test file not found: {test_file}")

    cities = set()
    with open(test_file) as f:
        for line in f:
            example = json.loads(line)
            cities.add((example['state'], example['city']))

    return sorted(cities)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate zone code extraction pipeline")
    parser.add_argument("--extractor-model", required=True,
                        help="Path to trained extractor model")
    parser.add_argument("--validator-model", default=None,
                        help="Path to trained validator model (optional, uses rule-based fallback if not provided)")
    parser.add_argument("--data-dir", default="model/zoning_codes_extract/training/data",
                        help="Directory with test split")
    parser.add_argument("--output-dir", default="model/zoning_codes_extract/evaluation/results",
                        help="Output directory for results")

    args = parser.parse_args()

    # Initialize pipeline
    print(f"Loading extractor model from {args.extractor_model}...")
    if args.validator_model:
        print(f"Loading validator model from {args.validator_model}...")
    else:
        print("No validator model provided, using rule-based fallback")

    pipeline = ZoningCodePipeline(
        extractor_model_path=args.extractor_model,
        validator_model_path=args.validator_model,
        min_validation_confidence=0.5,
        min_extraction_score=0.5
    )

    # Load test cities
    print(f"Loading test cities from {args.data_dir}...")
    test_cities = load_test_cities(args.data_dir)
    print(f"Found {len(test_cities)} test cities")

    # Evaluate
    evaluator = PipelineEvaluator(pipeline)
    aggregate = evaluator.evaluate_test_set(test_cities, args.output_dir)

    # Print results
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Test Cities: {aggregate['num_cities']}")
    print(f"\nMicro-averaged Metrics:")
    print(f"  Precision: {aggregate['micro_precision']:.3f}")
    print(f"  Recall: {aggregate['micro_recall']:.3f}")
    print(f"  F1: {aggregate['micro_f1']:.3f}")
    print(f"\nMacro-averaged Metrics:")
    print(f"  Precision: {aggregate['macro_precision']:.3f}")
    print(f"  Recall: {aggregate['macro_recall']:.3f}")
    print(f"  F1: {aggregate['macro_f1']:.3f}")
    print(f"\nTotal Counts:")
    print(f"  True Positives: {aggregate['total_true_positive']}")
    print(f"  False Positives: {aggregate['total_false_positive']}")
    print(f"  False Negatives: {aggregate['total_false_negative']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
