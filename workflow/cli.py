#!/usr/bin/env python3
"""CLI for running Vertex AI pipelines"""

import argparse
import os
import sys
from pathlib import Path


def load_env_file():
    """Load environment variables from secrets directory"""
    secrets_dir = Path(__file__).parent.parent / "secrets"
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


# Load environment variables before importing pipelines
load_env_file()

# Import pipelines and components
from pipelines.municode_ordinance import MunicodeOrdinancePipeline
from pipelines.municode_ordinance_parallel import MunicodeOrdinanceParallelPipeline
from pipelines.collector.municode_ordinance import MunicodeOrdinanceCollectorComponent
from pipelines.collector.municode_ordinance_parallel import MunicodeOrdinanceCollectorParallel
from pipelines.processor.municode_converter import DocxToMarkdownConverterComponent
from pipelines.processor.municode_converter_parallel import DocxToMarkdownConverterParallel

# Map to classes
available = {
    "collector": MunicodeOrdinanceCollectorComponent,
    "collector-parallel": MunicodeOrdinanceCollectorParallel,
    "processor": DocxToMarkdownConverterComponent,
    "processor-parallel": DocxToMarkdownConverterParallel,
    "pipeline": MunicodeOrdinancePipeline,
    "pipeline-parallel": MunicodeOrdinanceParallelPipeline,
}

# Modes that require a states list instead of a single state
multi_state_modes = {"collector-parallel", "processor-parallel", "pipeline-parallel"}


def run(state: str = None, mode: str = "pipeline", states: list[str] = None, exclude_states: list[str] = None):
    """
    Run a pipeline or component

    Args:
        state: State abbreviation (e.g., "ri", "ma", "ca")
        mode: Execution mode
            - "collector": Collector only (scrape DOCX files) for one state
            - "collector-parallel": Collector for multiple states in parallel
            - "processor": Processor only (convert DOCX to Markdown) for one state
            - "processor-parallel": Processor for multiple states in parallel
            - "pipeline": Full pipeline (collector + processor) for one state
            - "pipeline-parallel": Full pipeline for multiple states in parallel
        states: List of state abbreviations for parallel modes (optional)
        exclude_states: List of state abbreviations to exclude (optional)
    """
    if mode not in available:
        raise ValueError(
            f"Unknown mode: {mode}. "
            f"Available: {list(available.keys())}"
        )

    # Handle multi-state modes (parallel execution)
    if mode in multi_state_modes:
        if not states and not exclude_states:
            raise ValueError(
                f"--states is required for {mode}. "
                f"Use --states <abbrev1>,<abbrev2>,... (e.g., tx,fl,ga,al,ca)"
            )

        print(f"Running {mode}...")
        if states:
            print(f"Processing {len(states)} states: {', '.join(states)}")
            obj = available[mode](states=states)
        elif exclude_states:
            # Get all states and exclude the specified ones
            from pipelines.municode_ordinance_parallel import MunicodeOrdinanceParallelPipeline
            all_states = MunicodeOrdinanceParallelPipeline.US_STATES
            filtered_states = [s for s in all_states if s not in exclude_states]
            print(f"Excluding states: {', '.join(exclude_states)}")
            print(f"Processing {len(filtered_states)} states")
            obj = available[mode](states=filtered_states)
    # Handle single-state modes
    else:
        if not state:
            raise ValueError(
                f"--state is required for {mode}. "
                f"Use --state <abbrev> (e.g., ri, ma, ca)"
            )
        print(f"Running {mode} for {state}...")
        obj = available[mode](state=state)

    job = obj.run()

    print(f"Submitted successfully! Job: {job.display_name}")
    return job


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Vertex AI pipelines")
    parser.add_argument(
        "--state",
        type=str,
        help="State abbreviation (e.g., ri, ma, ca)",
        required=False,
    )
    parser.add_argument(
        "--mode",
        type=str,
        help="Execution mode (collector, collector-parallel, processor, processor-parallel, pipeline, pipeline-parallel)",
        required=True,
        choices=list(available.keys()),
    )
    parser.add_argument(
        "--states",
        type=str,
        help="Comma-separated list of state abbreviations for parallel modes (e.g., tx,fl,ga,al,ca)",
        required=False,
    )
    parser.add_argument(
        "--exclude-states",
        type=str,
        help="Comma-separated list of state abbreviations to exclude (e.g., al,ca,ri)",
        required=False,
    )

    args = parser.parse_args()

    # Parse states if provided for parallel pipeline
    states_list = None
    if args.states:
        states_list = [s.strip().lower() for s in args.states.split(",")]

    # Parse exclude states
    exclude_list = None
    if args.exclude_states:
        exclude_list = [s.strip().lower() for s in args.exclude_states.split(",")]

    # Run the selected mode
    run(state=args.state, mode=args.mode, states=states_list, exclude_states=exclude_list)
