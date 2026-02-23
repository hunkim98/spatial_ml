"""Build and push Docker images to GCP Artifact Registry"""

import argparse
import os
import subprocess
from pathlib import Path
from config import RegistryConfig


def load_env_file():
    """Load environment variables from secrets directory"""
    secrets_dir = Path(__file__).parent.parent.parent / "secrets"
    env_file = secrets_dir / "teamspatially-project.env"

    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

        sa_key = secrets_dir / "teamspatially-storage-accessor-keys.json"
        if sa_key.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(sa_key)


def ensure_repository_exists(gcp_region: str, gcp_project: str):
    """Ensure the Artifact Registry repository exists"""
    repo_name = RegistryConfig.repository_name()

    print(f"\nChecking if repository '{repo_name}' exists...")

    # Check if repository exists
    check_cmd = [
        "gcloud", "artifacts", "repositories", "describe", repo_name,
        "--location", gcp_region,
        "--project", gcp_project,
        "--format", "value(name)"
    ]

    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Repository '{repo_name}' already exists")
            return
    except Exception:
        pass

    # Create repository
    print(f"Creating repository '{repo_name}'...")
    create_cmd = [
        "gcloud", "artifacts", "repositories", "create", repo_name,
        "--repository-format", "docker",
        "--location", gcp_region,
        "--project", gcp_project,
        "--description", "Docker images for Spatial ML workflows"
    ]

    subprocess.run(create_cmd, check=True)
    print(f"Repository '{repo_name}' created successfully")


def build_and_push_image(image_config: dict):
    """Build and push a Docker image"""
    name = image_config["name"]
    context = image_config["context"]
    dockerfile = image_config["dockerfile"]
    image_uri = image_config["image_uri"]
    platform = image_config["platform"]

    print(f"\n{'='*60}")
    print(f"Building image: {name}")
    print(f"Context: {context}")
    print(f"Dockerfile: {dockerfile}")
    print(f"Image URI: {image_uri}")
    print(f"{'='*60}")

    # Build the image
    build_cmd = [
        "docker", "build",
        "--platform", platform,
        "-f", str(dockerfile),
        "-t", image_uri,
        str(context)
    ]

    print(f"\nBuilding image...")
    subprocess.run(build_cmd, check=True)
    print(f"✓ Image built successfully")

    # Push the image
    print(f"\nPushing image to {image_uri}...")
    push_cmd = ["docker", "push", image_uri]
    subprocess.run(push_cmd, check=True)
    print(f"✓ Image pushed successfully")


def main():
    parser = argparse.ArgumentParser(
        description="Build and push Docker images to GCP Artifact Registry"
    )
    parser.add_argument(
        "--images",
        type=str,
        default="all",
        help="Comma-separated list of images to build (collector,processor) or 'all'",
    )

    args = parser.parse_args()

    # Load environment variables
    load_env_file()

    # Get GCP configuration from environment
    gcp_project = os.environ["GCP_PROJECT"]
    gcp_region = os.environ["GCP_REGION"]

    print(f"\nGCP Project: {gcp_project}")
    print(f"GCP Region: {gcp_region}")

    # Ensure repository exists
    ensure_repository_exists(gcp_region, gcp_project)

    # Get all images
    all_images = RegistryConfig.images(gcp_region, gcp_project)

    # Filter images if specified
    if args.images.lower() != "all":
        requested = [img.strip() for img in args.images.split(",")]
        all_images = [img for img in all_images if img["name"] in requested]

    if not all_images:
        print("No images to build")
        return

    print(f"\nBuilding {len(all_images)} images:")
    for img in all_images:
        print(f"  - {img['name']}")

    # Build and push each image
    for image_config in all_images:
        try:
            build_and_push_image(image_config)
        except subprocess.CalledProcessError as e:
            print(f"\n✗ Error building/pushing {image_config['name']}: {e}")
            raise

    print(f"\n{'='*60}")
    print("All images built and pushed successfully!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
