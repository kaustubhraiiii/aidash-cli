"""Abstract base parser class."""

from abc import ABC, abstractmethod
from pathlib import Path

from aidash.models import Session


class BaseParser(ABC):
    @abstractmethod
    def discover_sessions(self) -> list[Path]:
        """Return a list of file paths for all discoverable sessions."""
        ...

    @abstractmethod
    def parse_session(self, filepath: Path) -> Session:
        """Parse a single session file into a Session object."""
        ...
