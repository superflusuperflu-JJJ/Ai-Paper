from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.paper import Paper


class Collector(ABC):
    name: str

    @abstractmethod
    def collect(self) -> list[Paper]:
        raise NotImplementedError
