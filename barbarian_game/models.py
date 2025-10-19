"""Core models for the Barbarian Saga WAP MMORPG."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

EQUIPMENT_SLOTS = ["weapon", "armor", "amulet", "helm", "trinket"]


@dataclass
class Stats:
    """Primary attributes for a hero."""

    strength: int = 0
    agility: int = 0
    spirit: int = 0
    endurance: int = 0
    wisdom: int = 0

    def merge(self, bonus: "Stats") -> "Stats":
        return Stats(
            strength=self.strength + bonus.strength,
            agility=self.agility + bonus.agility,
            spirit=self.spirit + bonus.spirit,
            endurance=self.endurance + bonus.endurance,
            wisdom=self.wisdom + bonus.wisdom,
        )

    def as_dict(self) -> Dict[str, int]:
        return {
            "strength": self.strength,
            "agility": self.agility,
            "spirit": self.spirit,
            "endurance": self.endurance,
            "wisdom": self.wisdom,
        }


@dataclass
class Item:
    """Equipment item that can provide stat bonuses."""

    name: str
    slot: str
    power: int
    rarity: str = "common"
    bonuses: Stats = field(default_factory=Stats)

    def __post_init__(self) -> None:
        if self.slot not in EQUIPMENT_SLOTS:
            raise ValueError(f"Unknown slot '{self.slot}'")


@dataclass
class Player:
    """Registered hero with stats, inventory and progression."""

    username: str
    password: str
    role: str = "player"
    stats: Stats = field(default_factory=lambda: Stats(10, 10, 10, 10, 10))
    level: int = 1
    experience: int = 0
    gold: int = 0
    energy: int = 100
    reputation: int = 0
    equipment: Dict[str, Item] = field(default_factory=dict)
    inventory: List[Item] = field(default_factory=list)

    def equip(self, item: Item) -> None:
        """Equip an item from inventory into its slot."""

        if item not in self.inventory:
            raise ValueError("Item is not in inventory")
        if item.slot not in EQUIPMENT_SLOTS:
            raise ValueError("Cannot equip unknown slot")
        previous = self.equipment.get(item.slot)
        self.equipment[item.slot] = item
        self.inventory.remove(item)
        if previous is not None:
            self.inventory.append(previous)

    def gain_item(self, item: Item) -> None:
        self.inventory.append(item)

    def gain_gold(self, amount: int) -> None:
        self.gold = max(0, self.gold + amount)

    def gain_experience(self, amount: int) -> None:
        self.experience += amount
        while self.experience >= self._next_level_threshold():
            self.experience -= self._next_level_threshold()
            self.level += 1
            self.stats = self.stats.merge(Stats(2, 1, 1, 2, 1))
            self.energy = min(120, self.energy + 10)
            self.reputation += 1

    def spend_energy(self, amount: int) -> None:
        if amount > self.energy:
            raise ValueError("Not enough energy")
        self.energy -= amount

    def restore_energy(self, amount: int) -> None:
        self.energy = min(120, self.energy + amount)

    def total_stats(self) -> Stats:
        merged = self.stats
        for item in self.equipment.values():
            merged = merged.merge(item.bonuses)
        return merged

    def power_score(self) -> int:
        stats = self.total_stats()
        return (
            stats.strength * 2
            + stats.agility * 2
            + stats.endurance * 3
            + stats.spirit
            + stats.wisdom
            + self.level * 5
        )

    def _next_level_threshold(self) -> int:
        return 150 + self.level * 50


@dataclass
class ChatMessage:
    username: str
    text: str


@dataclass
class EncounterResult:
    success: bool
    message: str
    loot: Optional[Item] = None
    gold: int = 0
    experience: int = 0
    reputation: int = 0


__all__ = ["Stats", "Item", "Player", "ChatMessage", "EncounterResult", "EQUIPMENT_SLOTS"]
