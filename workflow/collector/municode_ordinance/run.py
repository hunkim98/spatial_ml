"""Entry point for Municode ordinance collection pipeline"""

import argparse
from zoning_ordinance.batch_collect import BatchCollector

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, help="State abbreviation (e.g., ri, ma, ca)")
    args = parser.parse_args()

    state = args.state.lower()
    print(f"Collecting state: {state}")

    collector = BatchCollector(states=[state], discover_only=False, force=False)
    collector.run()

    print(f"Done: {state}")

if __name__ == "__main__":
    main()
