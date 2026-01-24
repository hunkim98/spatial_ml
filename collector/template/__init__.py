from abc import ABC, abstractmethod


class BaseCollector(ABC):

    @abstractmethod
    def collect(self):
        """Abstract method for collecting data. Must be implemented by subclasses."""
        pass


__all__ = ["BaseCollector"]
