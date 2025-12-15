from zoning_codes import ZoningCodesCollector
from utils.smart_arg_parser import SmartArgItem, SmartArgParser


if __name__ == "__main__":
    schema = {
        "source": SmartArgItem(
            flags=["--source"],
            prompt="The source to collect zoning codes for (choices: "
            + ", ".join(ZoningCodesCollector().collector_map.keys())
            + ")",
            arg_type=str,
            choices=[
                source.lower() for source in ZoningCodesCollector().collector_map.keys()
            ],
            required=True,
        ),
        "test_mode": SmartArgItem(
            flags=["--test-mode"],
            prompt="Run in test mode (only process first state with limited cities)",
            action="store_true",
            required=False,
        ),
        "state": SmartArgItem(
            flags=["--state"],
            prompt="Process only this state (e.g., 'california', 'new-york'). "
            "If not specified, processes all states.",
            arg_type=str,
            required=False,
            default=None,
        ),
        "max_workers": SmartArgItem(
            flags=["--max-workers"],
            prompt="Number of concurrent workers for processing cities (default: 4)",
            arg_type=int,
            required=False,
            default=4,
        ),
        "no_concurrent": SmartArgItem(
            flags=["--no-concurrent"],
            prompt="Disable concurrent processing (process cities sequentially)",
            action="store_true",
            required=False,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    max_workers = args.get("max_workers", 4)
    collector = ZoningCodesCollector(max_workers=max_workers)
    collector.collect(
        source=args["source"],
        test_mode=args.get("test_mode", False),
        state_slug=args.get("state"),
        use_concurrent=not args.get("no_concurrent", False),
    )

# example usage:
# python zoning_codes/run.py --source zoneomics --test-mode
# python zoning_codes/run.py --source zoneomics
# python zoning_codes/run.py --source zoneomics --state california
# python zoning_codes/run.py --source zoneomics --state california --max-workers 6
# python zoning_codes/run.py --source zoneomics --no-concurrent
