"""Game state and simulation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from random import random
from typing import List, Sequence

from .entities import Barbarian, EnemyCamp, ResourceCache, Village


class EncounterResult(Enum):
    """Outcome of an encounter."""

    VICTORY = auto()
    DEFEAT = auto()
    REST = auto()


@dataclass
class GameState:
    """High level state container for the game."""

    barbarian: Barbarian
    villages: List[Village] = field(default_factory=list)
    camps: List[EnemyCamp] = field(default_factory=list)
    caches: List[ResourceCache] = field(default_factory=list)
    message: str = "Начни путешествие!"

    def reset_destination(self, position: Sequence[float]) -> None:
        self.barbarian.destination = (float(position[0]), float(position[1]))

    def update(self, dt: float) -> None:
        if self.barbarian.recovering:
            self.barbarian.rest(dt)
            self.message = "Восстановление сил"
        else:
            self.barbarian.move(dt)
            self.message = "В пути..."
        self._check_collisions()

    def _check_collisions(self) -> None:
        bx, by = self.barbarian.position

        for camp in self.camps:
            if camp.defeated:
                continue
            cx, cy = camp.position
            if (bx - cx) ** 2 + (by - cy) ** 2 < 30 ** 2:
                if not self.barbarian.ready_for_battle():
                    self.message = f"{camp.name}: нужна выносливость"
                    return
                outcome = self._resolve_battle(camp)
                if outcome == EncounterResult.VICTORY:
                    self.message = f"{camp.name} повержен!"
                    camp.defeated = True
                    self.barbarian.apply_victory(camp.loot)
                else:
                    self.message = f"{camp.name} одолел героя"
                    self.barbarian.apply_defeat()
                return

        for village in self.villages:
            if village.liberated:
                continue
            vx, vy = village.position
            if (bx - vx) ** 2 + (by - vy) ** 2 < 28 ** 2:
                village.liberated = True
                reward = village.reward()
                self.barbarian.loot += reward
                self.message = f"{village.name} свободна (+{reward})"
                return

        for cache in self.caches:
            if cache.taken:
                continue
            rx, ry = cache.position
            if (bx - rx) ** 2 + (by - ry) ** 2 < 20 ** 2:
                recovered = cache.collect()
                self.barbarian.stamina = min(100.0, self.barbarian.stamina + recovered)
                self.message = "Запасы восполнили силы"
                return

    def _resolve_battle(self, camp: EnemyCamp) -> EncounterResult:
        barbarian_power = self.barbarian.strength + (self.barbarian.rage / 25.0)
        enemy_power = camp.power()
        luck = 0.85 + random() * 0.3
        if barbarian_power * luck >= enemy_power:
            self.barbarian.rage = min(100.0, self.barbarian.rage + 10.0)
            return EncounterResult.VICTORY
        self.barbarian.rage = max(0.0, self.barbarian.rage - 15.0)
        return EncounterResult.DEFEAT

    def remaining_objectives(self) -> int:
        return sum(1 for camp in self.camps if not camp.defeated) + sum(
            1 for village in self.villages if not village.liberated
        )

    def all_cleared(self) -> bool:
        return self.remaining_objectives() == 0
