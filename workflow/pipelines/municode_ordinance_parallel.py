"""Parallel pipeline for processing all US states simultaneously"""

from pipelines import BasePipeline
from kfp import dsl, compiler
import google.cloud.aiplatform as aip
from pipelines.collector.municode_ordinance import MunicodeOrdinanceCollectorComponent
from pipelines.processor.municode_converter import DocxToMarkdownConverterComponent


class MunicodeOrdinanceParallelPipeline(BasePipeline):
    """Parallel pipeline processing all US states"""

    # All US state abbreviations
    US_STATES = [
        "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga",
        "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md",
        "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj",
        "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc",
        "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy", "dc"
    ]

    def __init__(self, states: list[str] = None):
        """
        Initialize the parallel pipeline.

        Args:
            states: Optional list of state abbreviations. If None, processes all states.
        """
        super().__init__()
        self.pipeline_name = "municode-ordinance-parallel"
        self.states = [s.lower() for s in states] if states else self.US_STATES

    def create_pipeline(self):
        states = self.states

        @dsl.pipeline(name="municode-ordinance-parallel")
        def municode_parallel_pipeline():
            # Each state runs scraper→converter sequentially
            # All states run in parallel (no cross-state dependencies)
            for state in states:
                scraper = MunicodeOrdinanceCollectorComponent(state).get_component()
                converter = DocxToMarkdownConverterComponent(state).get_component()

                scraper_task = (
                    scraper()
                    .set_display_name(f"scraper-{state}")
                    .set_cpu_limit("2000m")
                    .set_memory_limit("8G")
                )

                converter_task = (
                    converter()
                    .set_display_name(f"converter-{state}")
                    .set_cpu_limit("2000m")
                    .set_memory_limit("4G")
                    .after(scraper_task)  # Wait for state's scraper
                )

        return municode_parallel_pipeline

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
        print(f"Processing {num_states} states in parallel")
        return job
