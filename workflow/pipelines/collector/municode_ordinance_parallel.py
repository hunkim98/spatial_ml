"""Parallel collector for processing multiple states simultaneously"""

from pipelines import BasePipeline
from kfp import dsl, compiler
import google.cloud.aiplatform as aip
from pipelines.collector.municode_ordinance import MunicodeOrdinanceCollectorComponent


class MunicodeOrdinanceCollectorParallel(BasePipeline):
    """Parallel collector processing multiple states"""

    def __init__(self, states: list[str]):
        """
        Initialize the parallel collector.

        Args:
            states: List of state abbreviations to process
        """
        super().__init__()
        self.pipeline_name = "municode-ordinance-collector-parallel"
        self.states = [s.lower() for s in states]

    def create_pipeline(self):
        states = self.states

        @dsl.pipeline(name="municode-ordinance-collector-parallel")
        def municode_collector_parallel_pipeline():
            # Each state runs collector in parallel
            for state in states:
                scraper = MunicodeOrdinanceCollectorComponent(state).get_component()

                scraper_task = (
                    scraper()
                    .set_display_name(f"collector-{state}")
                    .set_cpu_limit("2000m")
                    .set_memory_limit("8G")
                )

        return municode_collector_parallel_pipeline

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
        print(f"Processing {num_states} states in parallel (collector only)")
        return job
