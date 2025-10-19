"""Game entities used by the Barbarian mobile prototype."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

Vector2D = Tuple[float, float]


def lerp(current: float, target: float, ratio: float) -> float:
    """Linearly interpolate towards ``target`` with ``ratio``."""

    return current + (target - current) * ratio


@dataclass
class Barbarian:
    """Player-controlled barbarian hero."""

    position: Vector2D = (0.0, 0.0)
    strength: int = 1
    speed: float = 160.0
    stamina: float = 100.0
    rage: float = 0.0
    loot: int = 0
    level: int = 1
    destination: Vector2D = (0.0, 0.0)
    recovering: bool = False

    def move(self, dt: float) -> None:
        """Move the barbarian towards its destination."""

        if self.recovering:
            return

        x, y = self.position
        tx, ty = self.destination
        dx = tx - x
        dy = ty - y
        distance_sq = dx * dx + dy * dy
        if distance_sq < 4.0:
            self.position = self.destination
            return

        distance = distance_sq ** 0.5
        direction_x = dx / distance
        direction_y = dy / distance
        step = self.speed * dt
        new_x = x + direction_x * step
        new_y = y + direction_y * step
        self.position = (new_x, new_y)
        self.stamina = max(0.0, self.stamina - step * 0.1)
        self.rage = min(100.0, self.rage + step * 0.02)

    def rest(self, dt: float) -> None:
        """Recover stamina while resting."""

        self.recovering = True
        self.stamina = min(100.0, self.stamina + 15.0 * dt)
        self.rage = max(0.0, self.rage - 25.0 * dt)
        if self.stamina >= 99.0:
            self.recovering = False

    def ready_for_battle(self) -> bool:
        return self.stamina > 20.0

    def apply_victory(self, loot: int) -> None:
        self.loot += loot
        self.strength += 1
        if self.loot > self.level * 50:
            self.level += 1
            self.speed = lerp(self.speed, self.speed + 20.0, 0.5)

    def apply_defeat(self) -> None:
        self.recovering = True
        self.stamina = 10.0
        self.rage = max(0.0, self.rage - 10.0)


@dataclass
class Village:
    """Friendly settlement that can be liberated."""

    name: str
    position: Vector2D
    prosperity: int = 20
    liberated: bool = False

    def reward(self) -> int:
        return int(self.prosperity * 2.5)


@dataclass
class EnemyCamp:
    """Enemy location that the barbarian can raid."""

    name: str
    position: Vector2D
    strength: int
    loot: int
    enrages_on_attack: bool = False
    defeated: bool = False

    def power(self) -> int:
        return int(self.strength * (1.25 if self.enrages_on_attack else 1.0))


@dataclass
class ResourceCache:
    """Neutral location providing a stamina boost."""

    position: Vector2D
    amount: float = 40.0
    taken: bool = False

    def collect(self) -> float:
        if self.taken:
            return 0.0
        self.taken = True
        return self.amount
