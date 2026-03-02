"""
Configuration loader for training hyperparameters.

Loads hyperparameters from .env.training file with fallback to defaults.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class TrainingConfig:
    """Training configuration loaded from environment variables."""

    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            env_file: Path to .env file (defaults to .env.training in training dir)
        """
        # Load environment file
        if env_file is None:
            env_file = Path(__file__).parent.parent / ".env.training"

        if env_file.exists():
            load_dotenv(env_file, override=True)  # Override any previously loaded config
            print(f"Loaded training config from: {env_file}")
        else:
            print(f"Warning: Config file not found at {env_file}, using defaults")

        # Also load infrastructure .env if it exists
        root_env = Path(__file__).parent.parent.parent / ".env"
        if root_env.exists():
            load_dotenv(root_env, override=False)  # Don't override training config

        # GCP/GCS Configuration
        self.gcp_project = os.getenv("GCP_PROJECT", "")
        self.gcs_data_bucket = os.getenv("GCS_DATA_BUCKET", "spatially-data")
        self.gcs_model_bucket = os.getenv("GCS_MODEL_BUCKET", "spatially-models")

        # Model Configuration
        self.model_name = os.getenv("MODEL_NAME", "bert-base-uncased")
        self.seed = int(os.getenv("SEED", "42"))
        self.max_seq_length = int(os.getenv("MAX_SEQ_LENGTH", "512"))

        # Training Hyperparameters
        self.num_epochs = int(os.getenv("NUM_EPOCHS", "3"))
        self.batch_size = int(os.getenv("BATCH_SIZE", "2"))
        self.gradient_accumulation_steps = int(os.getenv("GRADIENT_ACCUMULATION_STEPS", "8"))
        self.learning_rate = float(os.getenv("LEARNING_RATE", "3e-5"))
        self.weight_decay = float(os.getenv("WEIGHT_DECAY", "0.01"))
        self.warmup_steps = int(os.getenv("WARMUP_STEPS", "50"))
        self.logging_steps = int(os.getenv("LOGGING_STEPS", "20"))

        # Model-Specific
        self.extractor_metric = os.getenv("EXTRACTOR_METRIC", "recall")
        self.validator_metric = os.getenv("VALIDATOR_METRIC", "f1")
        self.validator_neg_pos_ratio = float(os.getenv("VALIDATOR_NEG_POS_RATIO", "1.0"))

        # Data Preparation
        self.train_ratio = float(os.getenv("TRAIN_RATIO", "0.85"))
        self.test_ratio = float(os.getenv("TEST_RATIO", "0.15"))
        self.context_window = int(os.getenv("CONTEXT_WINDOW", "500"))
        self.max_passages_per_code = int(os.getenv("MAX_PASSAGES_PER_CODE", "10"))
        self.min_passages_per_code = int(os.getenv("MIN_PASSAGES_PER_CODE", "2"))

        # Inference Parameters
        self.min_extraction_score = float(os.getenv("MIN_EXTRACTION_SCORE", "0.5"))
        self.min_validation_confidence = float(os.getenv("MIN_VALIDATION_CONFIDENCE", "0.5"))
        self.extractor_overlap = int(os.getenv("EXTRACTOR_OVERLAP", "128"))
        self.validator_max_passages = int(os.getenv("VALIDATOR_MAX_PASSAGES", "5"))

        # Advanced Training
        self.gradient_checkpointing = bool(int(os.getenv("GRADIENT_CHECKPOINTING", "1")))
        self.precision = os.getenv("PRECISION", "none")  # none, fp16, bf16
        self.dataloader_workers = int(os.getenv("DATALOADER_WORKERS", "0"))
        self.pin_memory = bool(int(os.getenv("PIN_MEMORY", "0")))

        # Evaluation
        self.eval_strategy = os.getenv("EVAL_STRATEGY", "epoch")
        self.save_strategy = os.getenv("SAVE_STRATEGY", "epoch")
        self.load_best_model = bool(int(os.getenv("LOAD_BEST_MODEL", "1")))

        # Custom Tokenization (Extractor)
        self.use_custom_tokenization = bool(int(os.getenv("USE_CUSTOM_TOKENIZATION", "1")))
        self.use_enhanced_tags = bool(int(os.getenv("USE_ENHANCED_TAGS", "0")))

    @property
    def effective_batch_size(self) -> int:
        """Calculate effective batch size."""
        return self.batch_size * self.gradient_accumulation_steps

    @property
    def fp16(self) -> bool:
        """Whether to use fp16 precision."""
        return self.precision == "fp16"

    @property
    def bf16(self) -> bool:
        """Whether to use bf16 precision."""
        return self.precision == "bf16"

    def print_config(self, model_type: str = "model"):
        """
        Print configuration summary.

        Args:
            model_type: Type of model ('extractor' or 'validator')
        """
        print("\n" + "=" * 80)
        print(f"TRAINING CONFIGURATION - {model_type.upper()}")
        print("=" * 80)
        print(f"\n📦 Model Configuration:")
        print(f"  Base Model: {self.model_name}")
        print(f"  Max Sequence Length: {self.max_seq_length}")
        print(f"  Random Seed: {self.seed}")

        print(f"\n🎯 Training Hyperparameters:")
        print(f"  Epochs: {self.num_epochs}")
        print(f"  Batch Size: {self.batch_size}")
        print(f"  Gradient Accumulation Steps: {self.gradient_accumulation_steps}")
        print(f"  Effective Batch Size: {self.effective_batch_size}")
        print(f"  Learning Rate: {self.learning_rate}")
        print(f"  Weight Decay: {self.weight_decay}")
        print(f"  Warmup Steps: {self.warmup_steps}")

        print(f"\n📊 Evaluation:")
        if model_type == "extractor":
            print(f"  Best Model Metric: {self.extractor_metric}")
        else:
            print(f"  Best Model Metric: {self.validator_metric}")
        print(f"  Evaluation Strategy: {self.eval_strategy}")
        print(f"  Load Best Model: {self.load_best_model}")

        print(f"\n⚙️  Advanced:")
        print(f"  Gradient Checkpointing: {self.gradient_checkpointing}")
        print(f"  Precision: {self.precision}")
        print(f"  Dataloader Workers: {self.dataloader_workers}")

        if model_type == "extractor":
            print(f"\n🔧 Extractor-Specific:")
            print(f"  Custom Tokenization: {self.use_custom_tokenization}")
            print(f"  Enhanced BIO Tags: {self.use_enhanced_tags}")

        if model_type == "validator":
            print(f"\n🔧 Validator-Specific:")
            print(f"  Negative/Positive Ratio: {self.validator_neg_pos_ratio}")

        print("=" * 80 + "\n")


# Global config instance (can be imported directly)
config = TrainingConfig()


def get_config(env_file: Optional[Path] = None) -> TrainingConfig:
    """
    Get training configuration.

    Args:
        env_file: Optional path to .env file

    Returns:
        TrainingConfig instance
    """
    return TrainingConfig(env_file)


if __name__ == "__main__":
    # Test configuration loading
    cfg = get_config()
    cfg.print_config("extractor")
    cfg.print_config("validator")
