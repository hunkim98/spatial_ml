"""Entry point for DOCX to Markdown conversion pipeline"""

import argparse
import os
from converter import DocxToMarkdownConverter

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, help="State abbreviation (e.g., ri, ma, ca)")
    args = parser.parse_args()

    state = args.state.lower()
    gcp_project = os.environ["GCP_PROJECT"]
    bucket_name = os.environ["GCS_BUCKET_NAME"]

    print(f"GCP Project: {gcp_project}")
    print(f"Bucket: {bucket_name}")
    print(f"State: {state}")

    converter = DocxToMarkdownConverter(
        state=state,
        gcp_project=gcp_project,
        bucket_name=bucket_name,
    )
    converter.convert_state()

if __name__ == "__main__":
    main()
