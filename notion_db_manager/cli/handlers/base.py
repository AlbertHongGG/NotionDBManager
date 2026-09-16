from __future__ import annotations

import argparse
from abc import ABC, abstractmethod


class ActionHandler(ABC):
    """Base interface for category-specific CLI action handlers."""

    @abstractmethod
    def handle(self, args: argparse.Namespace) -> None:
        """Executes the command flow for the target action."""
        ...
