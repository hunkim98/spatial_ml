"""
Shared callbacks for model training.
"""

import gc
import time
from datetime import datetime, timedelta
import torch
from transformers import TrainerCallback


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


class MetricHighlightCallback(TrainerCallback):
    """Callback to highlight key metrics during training."""

    def __init__(self, metric_name: str, model_type: str):
        """
        Args:
            metric_name: Name of metric to highlight (e.g., 'recall', 'f1')
            model_type: Type of model ('extractor' or 'validator')
        """
        self.metric_name = metric_name
        self.model_type = model_type
        self.best_score = 0.0

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        if metrics and f"eval_{self.metric_name}" in metrics:
            score = metrics[f"eval_{self.metric_name}"]
            epoch = int(state.epoch) if state.epoch else 0

            if score > self.best_score:
                self.best_score = score
                improvement = "🎯 NEW BEST!"
            else:
                improvement = ""

            print(f"\n{'='*70}")
            print(f"📊 {self.model_type.upper()} - Epoch {epoch} - {self.metric_name.upper()}: {score:.4f} {improvement}")
            print(f"{'='*70}\n")

        return control


class ProgressCallback(TrainerCallback):
    """Enhanced progress tracking with ETA and visual feedback."""

    def __init__(self, model_type: str = "model"):
        """
        Args:
            model_type: Type of model being trained ('extractor' or 'validator')
        """
        self.model_type = model_type
        self.epoch_start_time = None
        self.training_start_time = None
        self.last_log_step = 0
        self.last_loss = None

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

        print(f"\n{'─' * 80}")
        print(f"📖 Epoch {epoch}/{int(args.num_train_epochs)} Starting...")
        print(f"{'─' * 80}\n")

    def on_log(self, args, state, control, logs=None, **kwargs):
        """Called when logging (every logging_steps)."""
        if logs and 'loss' in logs:
            self.last_loss = logs['loss']
            current_step = state.global_step
            total_steps = state.max_steps
            epoch = state.epoch

            # Calculate progress
            progress_pct = (current_step / total_steps) * 100
            steps_in_epoch = current_step - self.last_log_step
            self.last_log_step = current_step

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

    def on_epoch_end(self, args, state, control, **kwargs):
        """Called at the end of each epoch."""
        epoch = int(state.epoch) if state.epoch else 1
        epoch_time = time.time() - self.epoch_start_time if self.epoch_start_time else 0

        print(f"\n{'─' * 80}")
        print(f"✓ Epoch {epoch} Complete | Time: {timedelta(seconds=int(epoch_time))}")
        print(f"{'─' * 80}\n")

    def on_train_end(self, args, state, control, **kwargs):
        """Called at the end of training."""
        total_time = time.time() - self.training_start_time if self.training_start_time else 0

        print("\n" + "=" * 80)
        print(f"🎉 {self.model_type.upper()} Training Complete!")
        print("=" * 80)
        print(f"Total Time: {timedelta(seconds=int(total_time))}")
        print(f"Total Steps: {state.global_step}")
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")


class EpochProgressCallback(TrainerCallback):
    """Shows detailed progress for each epoch with statistics."""

    def __init__(self, model_type: str = "model"):
        self.model_type = model_type
        self.epoch_losses = []

    def on_log(self, args, state, control, logs=None, **kwargs):
        """Track losses during training."""
        if logs and 'loss' in logs:
            self.epoch_losses.append(logs['loss'])

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        """Print evaluation metrics with nice formatting."""
        if not metrics:
            return

        epoch = int(state.epoch) if state.epoch else 0

        print(f"\n{'═' * 80}")
        print(f"📊 EVALUATION RESULTS - Epoch {epoch}")
        print(f"{'═' * 80}")

        # Sort metrics for consistent display
        eval_metrics = {k: v for k, v in metrics.items() if k.startswith('eval_')}

        for key in sorted(eval_metrics.keys()):
            metric_name = key.replace('eval_', '')
            value = eval_metrics[key]

            # Format based on metric type
            if isinstance(value, float):
                # Highlight key metrics
                if metric_name in ['loss', 'accuracy', 'f1', 'precision', 'recall']:
                    print(f"  🎯 {metric_name.upper():<20} : {value:.4f}")
                else:
                    print(f"     {metric_name:<20} : {value:.4f}")
            else:
                print(f"     {metric_name:<20} : {value}")

        print(f"{'═' * 80}\n")

        # Reset epoch losses
        self.epoch_losses = []
