from abc import ABC, abstractmethod
import os
import random
import string
from pathlib import Path


class BasePipeline(ABC):
    """Base class for full pipelines"""

    def __init__(self):
        self.GCP_PROJECT = os.environ["GCP_PROJECT"]
        self.GCS_BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]
        self.BUCKET_URI = f"gs://{self.GCS_BUCKET_NAME}"
        self.PIPELINE_ROOT = f"{self.BUCKET_URI}/pipeline_root/root"
        self.GCS_SERVICE_ACCOUNT = os.environ["GCS_SERVICE_ACCOUNT"]
        self.GCS_PACKAGE_URI = os.environ.get("GCS_PACKAGE_URI", "")
        self.GCP_REGION = os.environ["GCP_REGION"]
        self.project_name = "spatial-ml"

        # Pipeline outputs directory for compiled YAML files
        workflow_dir = Path(__file__).parent.parent
        self.pipeline_outputs_dir = workflow_dir / "pipeline_outputs"
        self.pipeline_outputs_dir.mkdir(exist_ok=True)

    def generate_uuid(self, length: int = 8) -> str:
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    @abstractmethod
    def run(self):
        """Compile and submit the pipeline"""
        pass
