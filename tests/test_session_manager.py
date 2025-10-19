import unittest
from unittest.mock import patch

from barbarian_game import SessionManager


class TestSessionManager(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = SessionManager()
        self.manager.register("hero", "s3cret")
        authenticated = self.manager.authenticate("hero", "s3cret")
        assert authenticated, "Authentication should succeed during test setup"

    def test_chat_roundtrip(self) -> None:
        self.manager.post_message("hero", "Всем привет")
        self.assertIn("[hero] Всем привет", self.manager.formatted_chat())

    @patch("barbarian_game.session.random", return_value=0.8)
    @patch("barbarian_game.session.randint", side_effect=[2, 20])
    def test_arena_victory_updates_character(self, mock_randint, mock_random) -> None:
        char = self.manager.active_user.character  # type: ignore[union-attr]
        previous_loot = char.loot
        result = self.manager.simulate_arena()
        self.assertIn("Победа", result)
        self.assertGreater(char.loot, previous_loot)
        mock_randint.assert_called()
        mock_random.assert_called()

    @patch("barbarian_game.session.random", side_effect=[0.9, 0.1])
    @patch("barbarian_game.session.randint", side_effect=[10])
    def test_expedition_success_and_failure(self, mock_randint, mock_random) -> None:
        success_message = self.manager.start_expedition(0)
        self.assertIn("выполнена", success_message)
        failure_message = self.manager.start_expedition(1)
        self.assertIn("провалилась", failure_message)
        self.assertEqual("готова", self.manager.expeditions[1].status)
        self.assertEqual(mock_random.call_count, 2)

    @patch("barbarian_game.session.random", return_value=0.9)
    def test_boss_challenge_marks_defeated(self, mock_random) -> None:
        char = self.manager.active_user.character  # type: ignore[union-attr]
        char.strength = 5
        with patch("barbarian_game.session.randint", return_value=4):
            message = self.manager.challenge_boss(0)
        self.assertIn("пал", message)
        self.assertTrue(self.manager.bosses[0].defeated)


if __name__ == "__main__":
    unittest.main()
