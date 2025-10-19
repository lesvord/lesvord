import unittest

import main
from barbarian_game import SessionManager
from barbarian_game.models import Stats


class WAPGameTestCase(unittest.TestCase):
    def setUp(self) -> None:
        main.app.config["TESTING"] = True
        self.client = main.app.test_client()
        main.manager = SessionManager()
        self.manager = main.manager

    def register_and_login(self, username: str = "hero", password: str = "secret"):
        self.client.post("/register", data={"username": username, "password": password})
        self.client.post("/login", data={"username": username, "password": password})
        return self.manager.get_player(username)

    def test_registration_login_and_chat(self) -> None:
        player = self.register_and_login()
        self.assertIsNotNone(player)
        self.client.post("/chat", data={"message": "Привет клану"}, follow_redirects=True)
        last_message = self.manager.chat_log[-1]
        self.assertEqual(last_message.username, "hero")
        self.assertEqual(last_message.text, "Привет клану")

    def test_arena_and_expedition_rewards(self) -> None:
        player = self.register_and_login()
        player.stats = Stats(150, 150, 120, 140, 130)
        player.energy = 120
        player.inventory.clear()
        self.client.post("/arena", follow_redirects=True)
        self.assertGreaterEqual(player.gold, 35)
        self.assertGreaterEqual(player.experience, 90)
        inventory_before = len(player.inventory)
        self.client.post("/expedition/ashen_mires", follow_redirects=True)
        self.assertGreater(len(player.inventory), inventory_before)
        self.client.post("/equip", data={"index": "0"}, follow_redirects=True)
        self.assertIn("armor", player.equipment)
        self.assertEqual(player.equipment["armor"].name, "Плащ болотного странника")

    def test_boss_progression_requires_power(self) -> None:
        player = self.register_and_login()
        player.energy = 120
        # Первая попытка должна провалиться с базовыми статами
        self.client.post("/boss/golem_king", follow_redirects=True)
        self.assertFalse(any(item.name == "Корона титана" for item in player.inventory))
        # Усиливаем героя и пробуем снова
        player.stats = Stats(220, 220, 180, 210, 180)
        player.energy = 120
        self.client.post("/boss/golem_king", follow_redirects=True)
        self.assertTrue(any(item.name == "Корона титана" for item in player.inventory))

    def test_admin_panel_access(self) -> None:
        # Зарегистрировать героя и войти под админом
        self.register_and_login()
        self.client.post("/login", data={"username": "admin", "password": "admin"})
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Совет клана", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
