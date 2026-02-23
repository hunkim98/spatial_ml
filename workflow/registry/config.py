from pathlib import Path


class RegistryConfig:
    @staticmethod
    def repository_name():
        return "spatial-ml-workflows"

    @staticmethod
    def platform():
        """Platform for Docker builds (Vertex AI uses linux/amd64)"""
        return "linux/amd64"

    @staticmethod
    def municode_collector_image(gcp_region: str, gcp_project: str):
        """Municode ordinance collector with Selenium"""
        project_root = Path(__file__).parent.parent
        # Context is spatial_ml root (parent of workflow) to access collector/
        spatial_ml_root = project_root.parent
        return {
            "name": "municode-collector",
            "context": spatial_ml_root,
            "dockerfile": project_root / "collector" / "Dockerfile",
            "image_uri": f"{gcp_region}-docker.pkg.dev/{gcp_project}/{RegistryConfig.repository_name()}/municode-collector:latest",
            "platform": RegistryConfig.platform(),
        }

    @staticmethod
    def municode_processor_image(gcp_region: str, gcp_project: str):
        """DOCX to Markdown converter"""
        project_root = Path(__file__).parent.parent
        # Context is spatial_ml root for consistency
        spatial_ml_root = project_root.parent
        return {
            "name": "municode-processor",
            "context": spatial_ml_root,
            "dockerfile": project_root / "processor" / "Dockerfile",
            "image_uri": f"{gcp_region}-docker.pkg.dev/{gcp_project}/{RegistryConfig.repository_name()}/municode-processor:latest",
            "platform": RegistryConfig.platform(),
        }

    @staticmethod
    def images(gcp_region: str, gcp_project: str):
        return [
            RegistryConfig.municode_collector_image(gcp_region, gcp_project),
            RegistryConfig.municode_processor_image(gcp_region, gcp_project),
        ]
