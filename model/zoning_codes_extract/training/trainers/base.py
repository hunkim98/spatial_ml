"""
Base training infrastructure shared across all models.

Provides:
- Data loading from JSONL files
- Training loop setup with TrainingArguments
- Unified callbacks (MPS memory, progress tracking, metrics)
- GCS upload functionality
- WandB initialization
"""

import gc
import json
import os
import random
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import torch
import wandb
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from config import get_config


# ============================================================================
# Unified Callbacks
# ============================================================================

class MPSMemoryCallback(TrainerCallback):
    """Callback to clear MPS cache periodically to prevent memory buildup."""

    def on_step_end(self, args, state, control, **kwargs):
        if state.global_step % 100 == 0:
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            gc.collect()

    def on_epoch_end(self, args, state, control, **kwargs):
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        gc.collect()


class UnifiedProgressCallback(TrainerCallback):
    """
    Unified callback combining progress tracking and metric highlighting.

    Provides:
    - Training start/end summaries
    - Per-epoch progress tracking
    - Live loss and ETA updates
    - Evaluation metrics display with highlighting
    """

    def __init__(self, model_type: str = "model", highlight_metric: str = "f1"):
        """
        Args:
            model_type: Type of model being trained ('extractor' or 'validator')
            highlight_metric: Metric to highlight during evaluation (e.g., 'f1', 'recall')
        """
        self.model_type = model_type
        self.highlight_metric = highlight_metric
        self.best_score = 0.0
        self.epoch_start_time = None
        self.training_start_time = None
        self.last_log_step = 0
        self.last_loss = None
        self.epoch_losses = []

    def on_train_begin(self, args, state, control, **kwargs):
        """Called at the beginning of training."""
        self.training_start_time = time.time()
        total_steps = state.max_steps
        num_epochs = args.num_train_epochs

        print("\n" + "=" * 80)
        print(f"🚀 Starting {self.model_type.upper()} Training")
        print("=" * 80)
        print(f"Total Epochs: {num_epochs}")
        print(f"Total Steps: {total_steps}")
        print(f"Batch Size: {args.per_device_train_batch_size}")
        print(f"Gradient Accumulation: {args.gradient_accumulation_steps}")
        print(f"Effective Batch Size: {args.per_device_train_batch_size * args.gradient_accumulation_steps}")
        print(f"Learning Rate: {args.learning_rate}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")

    def on_epoch_begin(self, args, state, control, **kwargs):
        """Called at the beginning of each epoch."""
        self.epoch_start_time = time.time()
        epoch = int(state.epoch) if state.epoch else 1
        self.epoch_losses = []

        print(f"\n{'─' * 80}")
        print(f"📖 Epoch {epoch}/{int(args.num_train_epochs)} Starting...")
        print(f"{'─' * 80}\n")

    def on_log(self, args, state, control, logs=None, **kwargs):
        """Called when logging (every logging_steps)."""
        if logs and 'loss' in logs:
            self.last_loss = logs['loss']
            self.epoch_losses.append(logs['loss'])
            current_step = state.global_step
            total_steps = state.max_steps
            epoch = state.epoch

            # Calculate progress
            progress_pct = (current_step / total_steps) * 100

            # Calculate ETA
            if self.training_start_time:
                elapsed = time.time() - self.training_start_time
                steps_per_sec = current_step / elapsed if elapsed > 0 else 0
                remaining_steps = total_steps - current_step
                eta_seconds = remaining_steps / steps_per_sec if steps_per_sec > 0 else 0
                eta = str(timedelta(seconds=int(eta_seconds)))
            else:
                eta = "calculating..."

            # Create progress bar
            bar_length = 40
            filled = int(bar_length * current_step / total_steps)
            bar = '█' * filled + '░' * (bar_length - filled)

            # Print compact progress line
            print(f"[{bar}] {progress_pct:.1f}% | "
                  f"Step {current_step}/{total_steps} | "
                  f"Epoch {epoch:.2f} | "
                  f"Loss: {self.last_loss:.4f} | "
                  f"ETA: {eta}")

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        """Print evaluation metrics with highlighting."""
        if not metrics:
            return

        epoch = int(state.epoch) if state.epoch else 0

        print(f"\n{'═' * 80}")
        print(f"📊 EVALUATION RESULTS - Epoch {epoch}")
        print(f"{'═' * 80}")

        # Check for improvement in highlighted metric
        highlight_key = f"eval_{self.highlight_metric}"
        if highlight_key in metrics:
            score = metrics[highlight_key]
            if score > self.best_score:
                self.best_score = score
                improvement = "🎯 NEW BEST!"
            else:
                improvement = ""
        else:
            improvement = ""

        # Sort and display metrics
        eval_metrics = {k: v for k, v in metrics.items() if k.startswith('eval_')}

        for key in sorted(eval_metrics.keys()):
            metric_name = key.replace('eval_', '')
            value = eval_metrics[key]

            # Format based on metric type
            if isinstance(value, float):
                # Highlight key metrics
                is_key_metric = metric_name in ['loss', 'accuracy', 'f1', 'precision', 'recall']
                is_highlight = metric_name == self.highlight_metric
                prefix = "  🎯" if is_key_metric else "    "
                suffix = f" {improvement}" if is_highlight and improvement else ""
                print(f"{prefix} {metric_name.upper():<20} : {value:.4f}{suffix}")
            else:
                print(f"     {metric_name:<20} : {value}")

        print(f"{'═' * 80}\n")

        return control

    def on_epoch_end(self, args, state, control, **kwargs):
        """Called at the end of each epoch."""
        epoch = int(state.epoch) if state.epoch else 1
        epoch_time = time.time() - self.epoch_start_time if self.epoch_start_time else 0

        # Calculate average epoch loss
        avg_loss = np.mean(self.epoch_losses) if self.epoch_losses else self.last_loss

        print(f"\n{'─' * 80}")
        print(f"✓ Epoch {epoch} Complete | Time: {timedelta(seconds=int(epoch_time))} | Avg Loss: {avg_loss:.4f}" if avg_loss else f"✓ Epoch {epoch} Complete | Time: {timedelta(seconds=int(epoch_time))}")
        print(f"{'─' * 80}\n")

    def on_train_end(self, args, state, control, **kwargs):
        """Called at the end of training."""
        total_time = time.time() - self.training_start_time if self.training_start_time else 0

        print("\n" + "=" * 80)
        print(f"🎉 {self.model_type.upper()} Training Complete!")
        print("=" * 80)
        print(f"Total Time: {timedelta(seconds=int(total_time))}")
        print(f"Total Steps: {state.global_step}")
        print(f"Best {self.highlight_metric.upper()}: {self.best_score:.4f}")
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")


# ============================================================================
# Base Trainer Class
# ============================================================================

class BaseTrainer(ABC):
    """
    Abstract base class for model training.

    Provides shared functionality:
    - Configuration loading
    - Data loading from JSONL files
    - Training setup (arguments, callbacks)
    - Model saving and GCS upload
    - WandB initialization

    Subclasses must implement:
    - create_model() - Create the model instance
    - create_compute_metrics() - Create metrics computation function
    - create_data_collator() - Create data collator
    - get_model_type() - Return model type string ('extractor' or 'validator')
    """

    def __init__(self, config=None):
        """
        Initialize base trainer.

        Args:
            config: Configuration object (if None, loads from environment)
        """
        self.config = config or get_config()

        # Set seeds for reproducibility
        torch.manual_seed(self.config.seed)
        np.random.seed(self.config.seed)
        random.seed(self.config.seed)

        # Paths
        self.script_dir = Path(__file__).parent.parent.resolve()
        self.project_dir = self.script_dir.parent
        self.data_dir = self.script_dir / "data"
        self.output_dir = self.project_dir / "artifacts" / "models"

        # Model components (initialized during training)
        self.tokenizer: Optional[PreTrainedTokenizer] = None
        self.model: Optional[PreTrainedModel] = None
        self.trainer: Optional[Trainer] = None

    @abstractmethod
    def create_model(self, label_to_id: Dict, id_to_label: Dict) -> PreTrainedModel:
        """
        Create the model instance.

        Args:
            label_to_id: Mapping from labels to IDs
            id_to_label: Mapping from IDs to labels

        Returns:
            PreTrainedModel instance
        """
        pass

    @abstractmethod
    def create_compute_metrics(self, id_to_label: Dict):
        """
        Create metrics computation function.

        Args:
            id_to_label: Mapping from IDs to labels

        Returns:
            Function that computes metrics
        """
        pass

    @abstractmethod
    def create_data_collator(self):
        """
        Create data collator for batching.

        Returns:
            Data collator instance
        """
        pass

    @abstractmethod
    def get_model_type(self) -> str:
        """
        Get model type identifier.

        Returns:
            Model type string ('extractor' or 'validator')
        """
        pass

    @abstractmethod
    def load_examples_from_jsonl(
        self,
        file_path: Path,
        tokenizer: PreTrainedTokenizer,
        label_to_id: Dict[str, int]
    ) -> List[Dict]:
        """
        Load training examples from JSONL file.

        Args:
            file_path: Path to JSONL file
            tokenizer: Tokenizer instance
            label_to_id: Mapping from labels to IDs

        Returns:
            List of example dictionaries
        """
        pass

    def load_datasets(
        self,
        train_file: Optional[Path] = None,
        test_file: Optional[Path] = None
    ) -> Tuple[Dataset, Dataset, PreTrainedTokenizer, Dict, Dict]:
        """
        Load train and test datasets.

        Args:
            train_file: Path to training JSONL file (optional, uses default if None)
            test_file: Path to test JSONL file (optional, uses default if None)

        Returns:
            Tuple of (train_dataset, test_dataset, tokenizer, label_to_id, id_to_label)
        """
        # Use default paths if not provided
        if train_file is None:
            train_file = self.data_dir / f"train_{self.get_model_type()}.jsonl"
        if test_file is None:
            test_file = self.data_dir / f"test_{self.get_model_type()}.jsonl"

        if not train_file.exists():
            raise FileNotFoundError(f"Training data not found: {train_file}")
        if not test_file.exists():
            raise FileNotFoundError(f"Test data not found: {test_file}")

        # Get label mappings from subclass
        label_list = self.get_label_list()
        label_to_id = {label: i for i, label in enumerate(label_list)}
        id_to_label = {i: label for label, i in label_to_id.items()}

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        self.tokenizer = tokenizer

        # Load examples
        train_examples = self.load_examples_from_jsonl(train_file, tokenizer, label_to_id)
        test_examples = self.load_examples_from_jsonl(test_file, tokenizer, label_to_id)

        # Create datasets
        train_ds = Dataset.from_list(train_examples)
        test_ds = Dataset.from_list(test_examples)

        print(f"Loaded {len(train_examples)} train examples, {len(test_examples)} test examples")

        return train_ds, test_ds, tokenizer, label_to_id, id_to_label

    @abstractmethod
    def get_label_list(self) -> List[str]:
        """
        Get list of labels for this model type.

        Returns:
            List of label strings
        """
        pass

    def setup_wandb(self, run_name: str):
        """
        Initialize Weights & Biases logging.

        Args:
            run_name: Name for the WandB run
        """
        wandb_project = os.getenv("WANDB_PROJECT", "zoning-code-extraction")
        wandb_entity = os.getenv("WANDB_ENTITY", "spatially")

        wandb.init(
            project=wandb_project,
            entity=wandb_entity,
            name=run_name,
            config={
                "model_type": self.get_model_type(),
                "model_name": self.config.model_name,
                "num_epochs": self.config.num_epochs,
                "batch_size": self.config.batch_size,
                "learning_rate": self.config.learning_rate,
                "seed": self.config.seed,
            }
        )

    def create_training_arguments(self, output_dir: Path) -> TrainingArguments:
        """
        Create training arguments from configuration.

        Args:
            output_dir: Directory to save model outputs

        Returns:
            TrainingArguments instance
        """
        # Get model-specific metric for best model selection
        if self.get_model_type() == "extractor":
            metric_for_best = self.config.extractor_metric if hasattr(self.config, 'extractor_metric') else "f1"
        else:
            metric_for_best = self.config.validator_metric if hasattr(self.config, 'validator_metric') else "f1"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = f"{self.get_model_type()}_{timestamp}"

        return TrainingArguments(
            output_dir=str(output_dir),
            eval_strategy=self.config.eval_strategy,
            save_strategy=self.config.save_strategy,
            learning_rate=self.config.learning_rate,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            num_train_epochs=self.config.num_epochs,
            weight_decay=self.config.weight_decay,
            warmup_steps=self.config.warmup_steps,
            logging_steps=self.config.logging_steps,
            load_best_model_at_end=self.config.load_best_model,
            metric_for_best_model=metric_for_best,
            greater_is_better=True,
            seed=self.config.seed,
            report_to="wandb" if os.getenv("WANDB_API_KEY") else "none",
            run_name=run_name,
            dataloader_pin_memory=self.config.pin_memory,
            dataloader_num_workers=self.config.dataloader_workers,
            fp16=self.config.fp16,
            bf16=self.config.bf16,
            gradient_checkpointing=self.config.gradient_checkpointing,
            disable_tqdm=False,
            log_level="info",
        )

    def upload_to_gcs(
        self,
        model_dir: Path,
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        Upload trained model to Google Cloud Storage.

        Args:
            model_dir: Directory containing the saved model
            metadata: Metadata dictionary to include with upload

        Returns:
            GCS path if successful, None otherwise
        """
        upload_enabled = os.getenv("UPLOAD_TO_GCS", "0") == "1"
        if not upload_enabled:
            return None

        try:
            print("\n" + "=" * 60)
            print("Uploading model to GCS...")
            print("=" * 60)

            # Import GCS model manager
            sys.path.insert(0, str(self.script_dir / "utils"))
            from gcs_model_manager import upload_model_to_gcs

            # Add WandB URL if available
            if wandb.run is not None:
                metadata["wandb_url"] = wandb.run.get_url()

            # Upload model
            gcs_path = upload_model_to_gcs(
                model_dir=model_dir,
                model_type=self.get_model_type(),
                metadata=metadata
            )

            if gcs_path:
                print(f"✓ Model uploaded to: {gcs_path}")
                return gcs_path
            else:
                print("⚠ Model upload failed, but training completed successfully")
                return None

        except Exception as e:
            print(f"⚠ Failed to upload model to GCS: {e}")
            print("Training completed successfully, model saved locally")
            return None

    def save_model(
        self,
        trainer: Trainer,
        output_dir: Path,
        test_results: Dict[str, float]
    ):
        """
        Save model and verify all required files are present.

        Args:
            trainer: Trainer instance
            output_dir: Directory to save model
            test_results: Test evaluation results
        """
        print(f"\nSaving model to {output_dir}...")
        trainer.save_model(str(output_dir))
        self.tokenizer.save_pretrained(str(output_dir))
        print(f"✓ Model saved successfully")

        # Verify model files exist
        required_files = ['config.json', 'model.safetensors', 'tokenizer.json']
        missing_files = [f for f in required_files if not (output_dir / f).exists()]
        if missing_files:
            print(f"WARNING: Missing files: {missing_files}")
            print("Model may not load correctly!")
        else:
            print(f"✓ All required files present")

        # Save test results
        with open(output_dir / "test_results.json", 'w') as f:
            json.dump(test_results, f, indent=2)

    def train(
        self,
        train_file: Optional[Path] = None,
        test_file: Optional[Path] = None,
        highlight_metric: str = "f1"
    ) -> Tuple[Trainer, Dataset, PreTrainedTokenizer, Dict]:
        """
        Main training loop.

        Args:
            train_file: Path to training data (optional, uses default if None)
            test_file: Path to test data (optional, uses default if None)
            highlight_metric: Metric to highlight during training

        Returns:
            Tuple of (trainer, test_dataset, tokenizer, id_to_label)
        """
        print("\n" + "="*60)
        print(f"TRAINING {self.get_model_type().upper()} MODEL")
        print("="*60)

        # Load data
        train_ds, test_ds, tokenizer, label_to_id, id_to_label = self.load_datasets(train_file, test_file)

        # Create model
        model = self.create_model(label_to_id, id_to_label)
        self.model = model

        # Enable gradient checkpointing if configured
        if self.config.gradient_checkpointing:
            model.gradient_checkpointing_enable()

        # Create compute_metrics and data collator
        compute_metrics = self.create_compute_metrics(id_to_label)
        data_collator = self.create_data_collator()

        # Setup output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.output_dir / f"{self.get_model_type()}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Setup WandB if API key available
        if os.getenv("WANDB_API_KEY"):
            self.setup_wandb(f"{self.get_model_type()}_{timestamp}")

        # Create training arguments
        training_args = self.create_training_arguments(output_dir)

        # Create trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_ds,
            eval_dataset=test_ds,
            processing_class=tokenizer,
            data_collator=data_collator,
            compute_metrics=compute_metrics,
            callbacks=[
                MPSMemoryCallback(),
                UnifiedProgressCallback(self.get_model_type(), highlight_metric)
            ],
        )
        self.trainer = trainer

        # Train
        print("\nStarting training...")
        try:
            trainer.train()
        except KeyboardInterrupt:
            print("\n\nTraining interrupted by user. Saving current model state...")
        except Exception as e:
            print(f"\n\nTraining failed with error: {e}")
            print("Saving current model state...")
            raise

        # Evaluate on test set
        print("\n--- Test Set Evaluation ---")
        test_results = trainer.evaluate(test_ds)
        print(f"Test Results: {json.dumps(test_results, indent=2)}")

        # Save model
        self.save_model(trainer, output_dir, test_results)

        # Upload to GCS if enabled
        metadata = {
            "model_type": self.get_model_type(),
            "test_results": test_results,
            "training_config": {
                "model_name": self.config.model_name,
                "num_epochs": self.config.num_epochs,
                "batch_size": self.config.batch_size,
                "learning_rate": self.config.learning_rate,
            },
            "dataset_size": len(train_ds) + len(test_ds),
            "train_size": len(train_ds),
            "test_size": len(test_ds),
        }
        self.upload_to_gcs(output_dir, metadata)

        return trainer, test_ds, tokenizer, id_to_label
