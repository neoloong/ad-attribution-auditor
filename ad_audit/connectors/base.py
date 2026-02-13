"""Base class for API connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass
class ConnectorConfig:
    """Shared configuration for all connectors."""

    start_date: date | None = None
    end_date: date | None = None


class BaseConnector(ABC):
    """Abstract base class for data source connectors."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify that the connection is valid. Returns True on success."""
        ...

    @abstractmethod
    def fetch_data(self, config: ConnectorConfig | None = None) -> pd.DataFrame:
        """Pull data and return a normalized DataFrame."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name of this data source."""
        ...
