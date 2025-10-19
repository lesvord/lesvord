"""Session management and gameplay loops for the WAP MMORPG."""

from __future__ import annotations

from dataclasses import asdict
from secrets import token_hex
from typing import Dict, List, Optional

from .models import ChatMessage, EncounterResult, Item, Player, Stats


WORLD_MAP = """
   ⛰️  Северный хребет         🌊 Штормовой пролив
┌───────────────────────┬────────────────────────┐
│  Каменный круг        │  Равнина ветров        │
│  (столица клана)      │  Караваны торговцев    │
├───────────────────────┼────────────────────────┤
│  Пепельные топи       │  Гнездо духов          │
│  Заброшенные шахты    │  Святилище предков     │
└───────────────────────┴────────────────────────┘
""".strip()

ARENA_OPPONENT = {
    "name": "Ветеран стражи",
    "power": 260,
    "reward_xp": 90,
    "reward_gold": 35,
}

EXPEDITIONS = {
    "ashen_mires": {
        "title": "Пепельные топи",
        "difficulty": 240,
        "energy": 18,
        "gold": 55,
        "xp": 120,
        "item": Item(
            name="Плащ болотного странника",
            slot="armor",
            power=34,
            rarity="rare",
            bonuses=Stats(endurance=6, spirit=4),
        ),
    },
    "ancestral_shrine": {
        "title": "Святилище предков",
        "difficulty": 310,
        "energy": 22,
        "gold": 80,
        "xp": 160,
        "item": Item(
            name="Тотем мудреца",
            slot="amulet",
            power=42,
            rarity="epic",
            bonuses=Stats(spirit=6, wisdom=8),
        ),
    },
}

BOSSES = {
    "golem_king": {
        "title": "Король големов",
        "threshold": 320,
        "energy": 24,
        "reward": Item(
            name="Корона титана",
            slot="helm",
            power=55,
            rarity="legendary",
            bonuses=Stats(strength=8, endurance=8),
        ),
    },
    "abyssal_wyrm": {
        "title": "Бездна Змей",
        "threshold": 370,
        "energy": 28,
        "reward": Item(
            name="Сердце бездны",
            slot="trinket",
            power=60,
            rarity="legendary",
            bonuses=Stats(spirit=10, agility=6),
        ),
    },
}


class SessionManager:
    """Manage players, chat, encounters and admin overview."""

    def __init__(self) -> None:
        self.players: Dict[str, Player] = {}
        self.sessions: Dict[str, str] = {}
        self.chat_log: List[ChatMessage] = []
        self._seed_admin()

    # ------------------------------------------------------------------ account
    def _seed_admin(self) -> None:
        admin = Player(username="admin", password="admin", role="admin")
        admin.gain_item(
            Item(
                name="Боевой молот старейшины",
                slot="weapon",
                power=45,
                rarity="rare",
                bonuses=Stats(strength=6, endurance=4),
            )
        )
        self.players[admin.username] = admin
        self.chat_log.append(ChatMessage("система", "Админ клана вошёл в чат."))

    def register(self, username: str, password: str, role: str = "player") -> Player:
        username = username.strip()
        if not username or not password:
            raise ValueError("Введите имя и пароль")
        if username in self.players:
            raise ValueError("Такой герой уже существует")
        player = Player(username=username, password=password, role=role)
        # Стартовый набор
        starter_items = [
            Item(
                name="Боевой топор новичка",
                slot="weapon",
                power=25,
                bonuses=Stats(strength=4),
            ),
            Item(
                name="Кольчуга ветров",
                slot="armor",
                power=20,
                bonuses=Stats(endurance=3, agility=2),
            ),
        ]
        for item in starter_items:
            player.gain_item(item)
        player.equip(starter_items[0])
        player.equip(starter_items[1])
        self.players[username] = player
        self.chat_log.append(ChatMessage("система", f"{username} присоединился к клану!"))
        return player

    def authenticate(self, username: str, password: str) -> str:
        player = self.players.get(username)
        if not player or player.password != password:
            raise ValueError("Неверные данные")
        session_id = token_hex(16)
        self.sessions[session_id] = username
        return session_id

    def get_player(self, username: str) -> Optional[Player]:
        return self.players.get(username)

    def get_player_by_session(self, session_id: str) -> Optional[Player]:
        username = self.sessions.get(session_id)
        if not username:
            return None
        return self.players.get(username)

    # ------------------------------------------------------------------ chat
    def post_chat(self, username: str, text: str) -> ChatMessage:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Пустое сообщение")
        message = ChatMessage(username=username, text=cleaned)
        self.chat_log.append(message)
        self.chat_log = self.chat_log[-50:]
        return message

    # -------------------------------------------------------------- encounters
    def resolve_arena_duel(self, player: Player) -> EncounterResult:
        player.spend_energy(12)
        player_power = player.power_score()
        opponent_power = ARENA_OPPONENT["power"] + max(0, (player.level - 1) * 18)
        if player_power >= opponent_power:
            player.gain_gold(ARENA_OPPONENT["reward_gold"])
            player.gain_experience(ARENA_OPPONENT["reward_xp"])
            player.reputation += 2
            return EncounterResult(
                success=True,
                message=f"Вы одолели {ARENA_OPPONENT['name']}!",
                gold=ARENA_OPPONENT["reward_gold"],
                experience=ARENA_OPPONENT["reward_xp"],
                reputation=2,
            )
        player.restore_energy(4)
        return EncounterResult(
            success=False,
            message=f"{ARENA_OPPONENT['name']} оказался сильнее. Соберите снаряжение и попробуйте снова.",
        )

    def start_expedition(self, player: Player, zone_key: str) -> EncounterResult:
        expedition = EXPEDITIONS.get(zone_key)
        if not expedition:
            raise ValueError("Неизвестная зона экспедиции")
        player.spend_energy(expedition["energy"])
        power = player.power_score()
        success_threshold = expedition["difficulty"]
        if power + 40 >= success_threshold:
            player.gain_gold(expedition["gold"])
            player.gain_experience(expedition["xp"])
            player.reputation += 1
            loot = expedition["item"]
            player.gain_item(loot)
            return EncounterResult(
                success=True,
                message=f"Экспедиция в {expedition['title']} завершилась успехом!",
                loot=loot,
                gold=expedition["gold"],
                experience=expedition["xp"],
                reputation=1,
            )
        player.restore_energy(8)
        return EncounterResult(
            success=False,
            message=f"Экспедиция в {expedition['title']} провалилась. Герои спаслись, но без добычи.",
        )

    def challenge_boss(self, player: Player, boss_key: str) -> EncounterResult:
        boss = BOSSES.get(boss_key)
        if not boss:
            raise ValueError("Неизвестный босс")
        player.spend_energy(boss["energy"])
        threshold = boss["threshold"] + (player.level * 12)
        if player.power_score() >= threshold:
            reward: Item = boss["reward"]
            player.gain_item(reward)
            player.gain_gold(120)
            player.gain_experience(220)
            player.reputation += 3
            return EncounterResult(
                success=True,
                message=f"Босс {boss['title']} повержен!",
                loot=reward,
                gold=120,
                experience=220,
                reputation=3,
            )
        player.restore_energy(6)
        return EncounterResult(
            success=False,
            message=f"{boss['title']} слишком силён. Укрепите клан и возвращайтесь позже.",
        )

    # ---------------------------------------------------------------- utilities
    def serialise_player(self, player: Player) -> Dict[str, object]:
        data = {
            "username": player.username,
            "role": player.role,
            "level": player.level,
            "experience": player.experience,
            "energy": player.energy,
            "gold": player.gold,
            "reputation": player.reputation,
            "base_stats": player.stats.as_dict(),
            "total_stats": player.total_stats().as_dict(),
            "equipment": [
                {
                    "slot": slot,
                    "item": {
                        "name": item.name,
                        "power": item.power,
                        "rarity": item.rarity,
                        "bonuses": asdict(item.bonuses),
                    },
                }
                for slot, item in player.equipment.items()
            ],
            "inventory": [
                {
                    "name": item.name,
                    "slot": item.slot,
                    "power": item.power,
                    "rarity": item.rarity,
                }
                for item in player.inventory
            ],
        }
        return data

    def list_players(self) -> List[Dict[str, object]]:
        return [self.serialise_player(player) for player in self.players.values()]


__all__ = ["SessionManager", "WORLD_MAP", "EXPEDITIONS", "BOSSES", "ARENA_OPPONENT"]
