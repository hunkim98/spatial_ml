"""Parallel processor for converting multiple states simultaneously"""

from pipelines import BasePipeline
from kfp import dsl, compiler
import google.cloud.aiplatform as aip
from pipelines.processor.municode_converter import DocxToMarkdownConverterComponent


class DocxToMarkdownConverterParallel(BasePipeline):
    """Parallel processor converting multiple states"""

    def __init__(self, states: list[str]):
        """
        Initialize the parallel processor.

        Args:
            states: List of state abbreviations to process
        """
        super().__init__()
        self.pipeline_name = "municode-ordinance-processor-parallel"
        self.states = [s.lower() for s in states]

    def create_pipeline(self):
        states = self.states

        @dsl.pipeline(name="municode-ordinance-processor-parallel")
        def municode_processor_parallel_pipeline():
            # Each state runs processor in parallel
            for state in states:
                converter = DocxToMarkdownConverterComponent(state).get_component()

                converter_task = (
                    converter()
                    .set_display_name(f"processor-{state}")
                    .set_cpu_limit("2000m")
                    .set_memory_limit("4G")
                )

        return municode_processor_parallel_pipeline

    def run(self):
        """Compile and submit the pipeline to Vertex AI"""
        pipeline = self.create_pipeline()

        # Compile
        num_states = len(self.states)
        pipeline_file = self.pipeline_outputs_dir / f"{self.pipeline_name}_{num_states}states.yaml"
        compiler.Compiler().compile(pipeline, package_path=str(pipeline_file))

        # Initialize Vertex AI
        aip.init(project=self.GCP_PROJECT, staging_bucket=self.BUCKET_URI)

        # Submit job
        job_id = self.generate_uuid()
        display_name = f"{self.project_name}-{self.pipeline_name}-{num_states}states-{job_id}"

        job = aip.PipelineJob(
            display_name=display_name,
            template_path=str(pipeline_file),
            pipeline_root=self.PIPELINE_ROOT,
            enable_caching=False,
        )

        job.submit(service_account=self.GCS_SERVICE_ACCOUNT)

        print(f"Pipeline job submitted: {job.resource_name}")
        print(f"Processing {num_states} states in parallel (processor only)")
        return job
