"""DOCX to Markdown converter component for Vertex AI pipelines"""

from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class DocxToMarkdownConverterComponent(BaseComponent):
    """Converts DOCX files to Markdown for a given state"""

    def __init__(self, state: str):
        """
        Initialize the converter component.

        Args:
            state: State abbreviation (e.g., "ri", "ma", "ca")
        """
        super().__init__()
        self.state = state.lower()

    def get_component_name(self):
        return f"processor-municode-converter-{self.state}"

    def get_component(self):
        state = self.state
        gcs_bucket_name = self.GCS_BUCKET_NAME
        gcp_project = self.GCP_PROJECT

        @dsl.container_component
        def municode_converter_component():
            cmd = (
                f"export GCS_BUCKET_NAME={gcs_bucket_name} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"python /app/municode_converter/run.py "
                f"--state '{state}'"
            )
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.municode_processor_image(
                    self.GCP_REGION, self.GCP_PROJECT
                )["image_uri"],
                command=["bash", "-c", cmd],
            )
            return container_spec

        return municode_converter_component
