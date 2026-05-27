"""Handler registry — maps commands to their output processors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class HandlerSpec:
    name: str
    handler: Callable[[str], str]
    description: str


class HandlerRegistry:
    """Maps command names/prefixes to output handler callables.

    Handlers are callable that accept raw stdout text and return transformed text.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, HandlerSpec] = {}

    def register(self, command: str, handler: Callable[[str], str], description: str = "") -> None:
        self._handlers[command] = HandlerSpec(name=command, handler=handler, description=description)

    def get(self, command: str) -> HandlerSpec | None:
        return self._handlers.get(command)

    def dispatch(self, command: str, text: str) -> str:
        """Apply the registered handler for command, or return text unchanged."""
        spec = self._handlers.get(command)
        if spec is None:
            return text
        return spec.handler(text)

    def list_handlers(self) -> list[HandlerSpec]:
        return list(self._handlers.values())