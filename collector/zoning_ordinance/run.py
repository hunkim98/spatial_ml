import sys
from pathlib import Path

from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from zoning_ordinance import ZoningOrdinanceCollector

if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="Which city?",
            arg_type=str,
            required=True,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    collector = ZoningOrdinanceCollector()
    collector.collect(args["city"].lower())