"""Session and account management helpers for Barbarian Saga."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import randint, random
from typing import Dict, List, Optional

from .entities import Barbarian
from .state import GameState


@dataclass
class Character:
    """Playable character parameters tied to an account."""

    name: str
    level: int = 1
    strength: int = 2
    stamina: float = 100.0
    rage: float = 0.0
    loot: int = 0
    speed: float = 165.0

    def as_barbarian(self) -> Barbarian:
        """Create a ``Barbarian`` instance reflecting this character."""

        return Barbarian(
            position=(120.0, 160.0),
            destination=(320.0, 240.0),
            strength=self.strength,
            stamina=self.stamina,
            rage=self.rage,
            loot=self.loot,
            level=self.level,
            speed=self.speed,
        )

    def apply_victory(self, loot: int) -> str:
        self.loot += loot
        self.strength += 1
        if self.loot > self.level * 60:
            self.level += 1
            self.speed += 6
            return "Повышение уровня!"
        return ""

    def apply_defeat(self) -> None:
        self.rage = max(0.0, self.rage - 5.0)
        self.stamina = max(10.0, self.stamina - 20.0)


@dataclass
class UserAccount:
    """In-memory account with optional administrative privileges."""

    username: str
    password: str
    role: str = "player"
    character: Character = field(default_factory=lambda: Character(name="Герой"))

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


@dataclass
class ChatMessage:
    author: str
    text: str


@dataclass
class Expedition:
    name: str
    difficulty: str
    reward: int
    status: str = "готова"


@dataclass
class BossEncounter:
    name: str
    danger: int
    defeated: bool = False


class SessionManager:
    """Simple container that emulates multi-activity state."""

    def __init__(self) -> None:
        self._accounts: Dict[str, UserAccount] = {}
        self._active_user: Optional[UserAccount] = None
        self.chat_log: List[ChatMessage] = []
        self.expeditions: List[Expedition] = [
            Expedition("Разведка руин", "низкая", 25),
            Expedition("Обоз с припасами", "средняя", 40),
            Expedition("Штурм цитадели", "высокая", 85),
        ]
        self.bosses: List[BossEncounter] = [
            BossEncounter("Король кланов", 4),
            BossEncounter("Праматерь драконов", 6),
            BossEncounter("Древний титан", 9),
        ]

    # --- Account & auth management -------------------------------------------------
    def register(self, username: str, password: str, role: str = "player") -> UserAccount:
        if username in self._accounts:
            raise ValueError("Игрок с таким именем уже существует")
        character = Character(name=username or "Герой")
        if role == "admin":
            character.level = 3
            character.strength = 4
        account = UserAccount(username=username, password=password, role=role, character=character)
        self._accounts[username] = account
        return account

    def authenticate(self, username: str, password: str) -> bool:
        account = self._accounts.get(username)
        if not account or account.password != password:
            return False
        self._active_user = account
        return True

    def logout(self) -> None:
        self._active_user = None

    @property
    def active_user(self) -> Optional[UserAccount]:
        return self._active_user

    def all_accounts_summary(self) -> str:
        if not self._accounts:
            return "Нет зарегистрированных игроков"
        lines = []
        for account in self._accounts.values():
            role = "админ" if account.is_admin else "игрок"
            char = account.character
            lines.append(
                f"{account.username} ({role}) — ур.{char.level}, сила {char.strength}, добыча {char.loot}"
            )
        return "\n".join(lines)

    # --- Chat ----------------------------------------------------------------------
    def post_message(self, author: str, text: str) -> None:
        if not text.strip():
            return
        self.chat_log.append(ChatMessage(author=author, text=text.strip()))

    def formatted_chat(self) -> str:
        if not self.chat_log:
            return "Пока нет сообщений — начните беседу!"
        return "\n".join(f"[{msg.author}] {msg.text}" for msg in self.chat_log[-25:])

    # --- Arena, expeditions and bosses --------------------------------------------
    def simulate_arena(self) -> str:
        account = self.require_user()
        char = account.character
        opponent_power = randint(2, 6)
        hero_score = char.strength + random() * char.level
        if hero_score >= opponent_power:
            char.rage = min(100.0, char.rage + 10)
            bonus = randint(15, 30)
            level_message = char.apply_victory(bonus)
            return f"Победа! Награда: {bonus}. {level_message}"
        char.apply_defeat()
        return "Поражение, но опыт закален. Восстановите силы."

    def available_expeditions(self) -> List[Expedition]:
        return self.expeditions

    def start_expedition(self, index: int) -> str:
        account = self.require_user()
        try:
            expedition = self.expeditions[index]
        except IndexError as exc:
            raise ValueError("Неизвестная экспедиция") from exc
        if expedition.status == "выполнена":
            return "Эта экспедиция уже завершена"
        expedition.status = "выполняется"
        success = random() > 0.3
        if success:
            expedition.status = "выполнена"
            bonus = expedition.reward + randint(5, 20)
            account.character.apply_victory(bonus)
            return f"Экспедиция '{expedition.name}' выполнена! Добыча: {bonus}"
        expedition.status = "готова"
        account.character.apply_defeat()
        return f"Экспедиция '{expedition.name}' провалилась. Герою нужен отдых"

    def boss_summary(self) -> str:
        parts = []
        for boss in self.bosses:
            status = "повержен" if boss.defeated else "ожидает"
            parts.append(f"{boss.name} — опасность {boss.danger}/10 ({status})")
        return "\n".join(parts)

    def challenge_boss(self, index: int) -> str:
        account = self.require_user()
        try:
            boss = self.bosses[index]
        except IndexError as exc:
            raise ValueError("Неизвестный босс") from exc
        if boss.defeated:
            return "Этот босс уже повержен"
        char = account.character
        hero_power = char.strength + char.level + random() * 3
        if hero_power >= boss.danger + 3:
            boss.defeated = True
            reward = 100 + boss.danger * 10
            char.apply_victory(reward)
            return f"{boss.name} пал! Герой получает {reward} славы"
        char.apply_defeat()
        return f"{boss.name} оказался слишком силён. Возвращайтесь сильнее"

    # --- Utilities -----------------------------------------------------------------
    def create_game_state(self) -> GameState:
        account = self.require_user()
        barbarian = account.character.as_barbarian()
        return GameState.default(barbarian)

    def require_user(self) -> UserAccount:
        if not self._active_user:
            raise RuntimeError("Нет активного пользователя")
        return self._active_user
