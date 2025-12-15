from abc import ABC, abstractmethod


class BaseProcessor(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def source_directory(self):
        """Abstract method for getting the source directory. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def process(self):
        """Abstract method for processing data. Must be implemented by subclasses."""
        pass


__all__ = ["BaseProcessor"]
