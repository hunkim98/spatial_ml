#!/usr/bin/env python3
"""
Unified training CLI for zoning code extraction models.

This script replaces the previous collection of shell scripts with a single
Python CLI interface for all training operations.

Usage:
    # Train extractor model
    python -m training.train extractor

    # Train validator model
    python -m training.train validator

    # Train both models sequentially
    python -m training.train pipeline

    # Prepare data for specific states
    python -m training.train prepare extractor --states california texas
    python -m training.train prepare validator --states california

    # Evaluate models
    python -m training.train evaluate

    # Show configuration
    python -m training.train config
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def train_extractor(args):
    """Train extractor model."""
    from training.trainers import ExtractorTrainer
    from training.utils.config import get_config

    print("\n" + "=" * 80)
    print("TRAINING EXTRACTOR MODEL")
    print("=" * 80)

    # Load config from specified file or default
    config = get_config(Path(args.config) if hasattr(args, 'config') and args.config else None)
    trainer = ExtractorTrainer(config=config)

    # Override config if command-line args provided
    if args.epochs:
        trainer.config.num_epochs = args.epochs
    if args.batch_size:
        trainer.config.batch_size = args.batch_size
    if args.learning_rate:
        trainer.config.learning_rate = args.learning_rate

    # Print config
    trainer.config.print_config("extractor")

    # Train
    trainer.train(highlight_metric=args.metric or "recall")

    print("\n✓ Extractor training complete!")


def train_validator(args):
    """Train validator model."""
    from training.trainers import ValidatorTrainer
    from training.utils.config import get_config

    print("\n" + "=" * 80)
    print("TRAINING VALIDATOR MODEL")
    print("=" * 80)

    # Load config from specified file or default
    config = get_config(Path(args.config) if hasattr(args, 'config') and args.config else None)
    trainer = ValidatorTrainer(config=config)

    # Override config if command-line args provided
    if args.epochs:
        trainer.config.num_epochs = args.epochs
    if args.batch_size:
        trainer.config.batch_size = args.batch_size
    if args.learning_rate:
        trainer.config.learning_rate = args.learning_rate

    # Print config
    trainer.config.print_config("validator")

    # Train
    trainer.train(highlight_metric=args.metric or "f1")

    print("\n✓ Validator training complete!")


def train_pipeline(args):
    """Train both models sequentially."""
    print("\n" + "=" * 80)
    print("TRAINING FULL PIPELINE (Extractor → Validator)")
    print("=" * 80)

    # Train extractor first
    print("\n📦 Stage 1/2: Training Extractor...")
    train_extractor(args)

    # Train validator second
    print("\n📦 Stage 2/2: Training Validator...")
    train_validator(args)

    print("\n" + "=" * 80)
    print("✓ FULL PIPELINE TRAINING COMPLETE!")
    print("=" * 80)


def prepare_extractor_data(args):
    """Prepare extractor training data."""
    from training.data_prep.prepare_extractor import main as prepare_main

    print("\n" + "=" * 80)
    print("PREPARING EXTRACTOR DATA")
    print("=" * 80)

    # Call existing data preparation script
    # Override sys.argv for the prepare script
    old_argv = sys.argv
    sys.argv = ['prepare_extractor.py', '--use-gcs']  # Always fetch from GCS
    if hasattr(args, 'states') and args.states:
        sys.argv.extend(['--states'] + args.states)
    if hasattr(args, 'output_dir') and args.output_dir:
        sys.argv.extend(['--output-dir', args.output_dir])

    try:
        prepare_main()
    finally:
        sys.argv = old_argv

    print("\n✓ Extractor data preparation complete!")


def prepare_validator_data(args):
    """Prepare validator training data."""
    from training.data_prep.prepare_validator import main as prepare_main

    print("\n" + "=" * 80)
    print("PREPARING VALIDATOR DATA")
    print("=" * 80)

    # Call existing data preparation script
    old_argv = sys.argv
    sys.argv = ['prepare_validator.py', '--use-gcs']  # Always fetch from GCS
    if hasattr(args, 'states') and args.states:
        sys.argv.extend(['--states'] + args.states)
    if hasattr(args, 'output_dir') and args.output_dir:
        sys.argv.extend(['--output-dir', args.output_dir])

    try:
        prepare_main()
    finally:
        sys.argv = old_argv

    print("\n✓ Validator data preparation complete!")


def evaluate_models(args):
    """Evaluate trained models and generate dashboard cache."""
    from evaluation.compute_metrics import main as compute_main

    print("\n" + "=" * 80)
    print("EVALUATING MODELS")
    print("=" * 80)

    # Call evaluation script
    old_argv = sys.argv
    sys.argv = ['compute_metrics.py']
    if args.extractor:
        sys.argv.extend(['--extractor', args.extractor])
    if args.validator:
        sys.argv.extend(['--validator', args.validator])

    try:
        compute_main()
    finally:
        sys.argv = old_argv

    print("\n✓ Evaluation complete!")


def show_config(args):
    """Show current training configuration."""
    from training.utils.config import get_config

    config = get_config()

    print("\n" + "=" * 80)
    print("CURRENT TRAINING CONFIGURATION")
    print("=" * 80)

    config.print_config("extractor")
    config.print_config("validator")

    # Show environment info
    import os
    print("\n" + "=" * 80)
    print("ENVIRONMENT CONFIGURATION")
    print("=" * 80)
    print(f"\n🌍 Environment:")
    print(f"  WANDB_PROJECT: {os.getenv('WANDB_PROJECT', 'Not set')}")
    print(f"  WANDB_ENTITY: {os.getenv('WANDB_ENTITY', 'Not set')}")
    print(f"  WANDB_API_KEY: {'Set' if os.getenv('WANDB_API_KEY') else 'Not set'}")
    print(f"  GCP_PROJECT: {os.getenv('GCP_PROJECT', 'Not set')}")
    print(f"  GCS_DATA_BUCKET: {os.getenv('GCS_DATA_BUCKET', 'Not set')}")
    print(f"  GCS_MODEL_BUCKET: {os.getenv('GCS_MODEL_BUCKET', 'Not set')}")
    print(f"  UPLOAD_TO_GCS: {os.getenv('UPLOAD_TO_GCS', '0')}")
    print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Unified training CLI for zoning code extraction models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Prepare data for specific states
  python -m training.train prepare extractor --states california texas
  python -m training.train prepare validator --states california

  # Train with specific config file (local vs cloud)
  python -m training.train extractor --config training/.env.training.local
  python -m training.train validator --config training/.env.training.cloud

  # Full pipeline (prepare + train)
  python -m training.train pipeline --config training/.env.training.local

  # Override specific hyperparameters
  python -m training.train extractor --config training/.env.training.cloud --epochs 10

  # Show configuration
  python -m training.train config

Note: For easier usage, use the unified shell script:
  ./training/scripts/train.sh --model extractor --states california --config local
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    subparsers.required = True

    # Extractor command
    extractor_parser = subparsers.add_parser('extractor', help='Train extractor model')
    extractor_parser.add_argument('--config', type=str, help='Path to training config file (e.g., training/.env.training.local)')
    extractor_parser.add_argument('--epochs', type=int, help='Number of training epochs')
    extractor_parser.add_argument('--batch-size', type=int, help='Batch size')
    extractor_parser.add_argument('--learning-rate', type=float, help='Learning rate')
    extractor_parser.add_argument('--metric', type=str, choices=['f1', 'precision', 'recall'],
                                   help='Metric to highlight (default: recall)')
    extractor_parser.set_defaults(func=train_extractor)

    # Validator command
    validator_parser = subparsers.add_parser('validator', help='Train validator model')
    validator_parser.add_argument('--config', type=str, help='Path to training config file (e.g., training/.env.training.local)')
    validator_parser.add_argument('--epochs', type=int, help='Number of training epochs')
    validator_parser.add_argument('--batch-size', type=int, help='Batch size')
    validator_parser.add_argument('--learning-rate', type=float, help='Learning rate')
    validator_parser.add_argument('--metric', type=str, choices=['f1', 'precision', 'recall', 'accuracy'],
                                   help='Metric to highlight (default: f1)')
    validator_parser.set_defaults(func=train_validator)

    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Train both models sequentially')
    pipeline_parser.add_argument('--config', type=str, help='Path to training config file (e.g., training/.env.training.cloud)')
    pipeline_parser.add_argument('--epochs', type=int, help='Number of training epochs')
    pipeline_parser.add_argument('--batch-size', type=int, help='Batch size')
    pipeline_parser.add_argument('--learning-rate', type=float, help='Learning rate')
    pipeline_parser.set_defaults(func=train_pipeline)

    # Prepare command
    prepare_parser = subparsers.add_parser('prepare', help='Prepare training data')
    prepare_subparsers = prepare_parser.add_subparsers(dest='model_type', help='Model type')
    prepare_subparsers.required = True

    # Prepare extractor
    prepare_extractor_parser = prepare_subparsers.add_parser('extractor', help='Prepare extractor data')
    prepare_extractor_parser.add_argument('--states', nargs='+', help='States to include (e.g., california texas)')
    prepare_extractor_parser.add_argument('--output-dir', type=str, help='Output directory')
    prepare_extractor_parser.set_defaults(func=prepare_extractor_data)

    # Prepare validator
    prepare_validator_parser = prepare_subparsers.add_parser('validator', help='Prepare validator data')
    prepare_validator_parser.add_argument('--states', nargs='+', help='States to include (e.g., california texas)')
    prepare_validator_parser.add_argument('--output-dir', type=str, help='Output directory')
    prepare_validator_parser.set_defaults(func=prepare_validator_data)

    # Evaluate command
    evaluate_parser = subparsers.add_parser('evaluate', help='Evaluate trained models')
    evaluate_parser.add_argument('--extractor', type=str, default=None, help='Extractor model name (auto-detected if omitted)')
    evaluate_parser.add_argument('--validator', type=str, default=None, help='Validator model name (auto-detected if omitted)')
    evaluate_parser.set_defaults(func=evaluate_models)

    # Config command
    config_parser = subparsers.add_parser('config', help='Show current configuration')
    config_parser.set_defaults(func=show_config)

    # Parse arguments
    args = parser.parse_args()

    # Execute command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
