"""Single-state Municode ordinance collection and conversion pipeline"""

from pipelines import BasePipeline
from kfp import dsl, compiler
import google.cloud.aiplatform as aip
from pipelines.collector.municode_ordinance import MunicodeOrdinanceCollectorComponent
from pipelines.processor.municode_converter import DocxToMarkdownConverterComponent


class MunicodeOrdinancePipeline(BasePipeline):
    """Single-state pipeline for scraping and converting Municode ordinances"""

    def __init__(self, state: str):
        """
        Initialize the pipeline.

        Args:
            state: State abbreviation (e.g., "ri", "ma", "ca")
        """
        super().__init__()
        self.pipeline_name = "municode-ordinance"
        self.state = state.lower()

    def create_pipeline(self):
        state = self.state

        # Initialize components
        scraper = MunicodeOrdinanceCollectorComponent(state).get_component()
        converter = DocxToMarkdownConverterComponent(state).get_component()

        @dsl.pipeline(name=f"municode-ordinance-{state}")
        def municode_pipeline():
            # Step 1: Scrape DOCX files
            scraper_task = (
                scraper()
                .set_display_name(f"scraper-{state}")
                .set_cpu_limit("2000m")
                .set_memory_limit("8G")
            )

            # Step 2: Convert to Markdown (waits for scraper)
            converter_task = (
                converter()
                .set_display_name(f"converter-{state}")
                .set_cpu_limit("2000m")
                .set_memory_limit("4G")
                .after(scraper_task)  # Sequential dependency
            )

        return municode_pipeline

    def run(self):
        """Compile and submit the pipeline to Vertex AI"""
        pipeline = self.create_pipeline()

        # Compile
        pipeline_file = self.pipeline_outputs_dir / f"{self.pipeline_name}_{self.state}.yaml"
        compiler.Compiler().compile(pipeline, package_path=str(pipeline_file))

        # Initialize Vertex AI
        aip.init(project=self.GCP_PROJECT, staging_bucket=self.BUCKET_URI)

        # Submit job
        job_id = self.generate_uuid()
        display_name = f"{self.project_name}-{self.pipeline_name}-{self.state}-{job_id}"

        job = aip.PipelineJob(
            display_name=display_name,
            template_path=str(pipeline_file),
            pipeline_root=self.PIPELINE_ROOT,
            enable_caching=False,
        )

        job.submit(service_account=self.GCS_SERVICE_ACCOUNT)

        print(f"Pipeline job submitted: {job.resource_name}")
        return job
