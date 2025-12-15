from .zoneomics import ZoneomicsCollector


class ZoningCodesCollector:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.collector_map = {
            "zoneomics": ZoneomicsCollector,
        }

    def collect(
        self,
        source: str,
        test_mode: bool = False,
        state_slug: str = None,
        use_concurrent: bool = True,
    ):
        """
        Collect zoning codes from the specified source.

        Args:
            source: Data source to collect from (e.g., "zoneomics")
            test_mode: If True, only process first state and limited cities
            state_slug: If provided, only process this specific state (e.g., "california")
            use_concurrent: If True, process cities concurrently within each state

        Returns:
            dict with processed, skipped, and error counts
        """
        if source not in self.collector_map:
            raise ValueError(
                f"Unsupported source: {source}. Available: {list(self.collector_map.keys())}"
            )

        collector = self.collector_map[source](max_workers=self.max_workers)
        return collector.collect(
            test_mode=test_mode,
            state_slug=state_slug,
            use_concurrent=use_concurrent,
        )

    @staticmethod
    def get_all_state_slugs() -> list[str]:
        """Return list of all valid state slugs for parallel processing."""
        return [slug for _, slug in ZoneomicsCollector.US_STATES]
