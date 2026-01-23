from .cambridge import CambridgeZoningOrdinanceCollector
from .boston import BostonZoningOrdinanceCollector
from .municode import MunicodeZoningOrdinanceCollector


class ZoningOrdinanceCollector:
    def __init__(self):
        self.collector_map = {
            "cambridge": CambridgeZoningOrdinanceCollector,
            "boston": BostonZoningOrdinanceCollector,
        }

    def collect(self, city: str):
        if city not in self.collector_map:
            raise ValueError(f"Unsupported city: {city}. Available: {list(self.collector_map.keys())}")

        print(f"Collecting zoning ordinance for {city}")
        return self.collector_map[city]().collect()

    def collect_municode(self, state_abbrev: str, municipality: str):
        """
        Collect zoning ordinance from any Municode municipality.

        Args:
            state_abbrev: Two-letter state abbreviation (e.g., 'ma', 'al')
            municipality: Municipality name (e.g., 'boston', 'birmingham')

        Returns:
            List of downloaded files

        Example:
            collector = ZoningOrdinanceCollector()
            collector.collect_municode('al', 'birmingham')
        """
        municode_collector = MunicodeZoningOrdinanceCollector.from_state_and_municipality(
            state_abbrev=state_abbrev,
            municipality=municipality
        )
        if municode_collector is None:
            raise ValueError(
                f"Could not find codes URL for {municipality}, {state_abbrev.upper()}"
            )
        return municode_collector.collect()