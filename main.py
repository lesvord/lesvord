"""Barbarian Saga – multi-activity mobile friendly prototype."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Tuple

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.widget import Widget

from barbarian_game import GameState, SessionManager

ASSETS_DIR = Path(__file__).parent / "barbarian_game"
Builder.load_file(str(ASSETS_DIR / "barbarian.kv"))


class RootManager(ScreenManager):
    """Top-level screen manager with animated transitions."""

    def __init__(self, **kwargs):
        super().__init__(transition=FadeTransition(duration=0.3), **kwargs)


class LandingScreen(Screen):
    """Entry point guiding players to login or registration."""


class RegisterScreen(Screen):
    """Simple registration form."""

    message = StringProperty("")

    def submit(self) -> None:
        app = App.get_running_app()
        username = self.ids.reg_username.text.strip()
        password = self.ids.reg_password.text.strip()
        role = self.ids.reg_role.text.strip() or "player"
        if not username or not password:
            self.message = "Укажите имя и пароль"
            return
        try:
            app.session_manager.register(username, password, role)
        except ValueError as exc:  # username conflict
            self.message = str(exc)
            return
        self.message = "Аккаунт создан! Перейдите к авторизации"
        self.ids.reg_username.text = ""
        self.ids.reg_password.text = ""
        self.ids.reg_role.text = "player"


class LoginScreen(Screen):
    """Authentication form."""

    message = StringProperty("")

    def submit(self) -> None:
        app = App.get_running_app()
        username = self.ids.login_username.text.strip()
        password = self.ids.login_password.text.strip()
        if not username or not password:
            self.message = "Введите учетные данные"
            return
        if app.session_manager.authenticate(username, password):
            self.message = "Успешный вход"
            self.manager.current = "hub"
            self.ids.login_password.text = ""
        else:
            self.message = "Неверный логин или пароль"


class HubScreen(Screen):
    """Main activity hub."""

    greeting = StringProperty("")
    role_hint = StringProperty("")

    def on_pre_enter(self, *args):  # type: ignore[override]
        app = App.get_running_app()
        user = app.session_manager.active_user
        if not user:
            self.greeting = "Гость"
            self.role_hint = "Авторизуйтесь, чтобы продолжить"
            return
        self.greeting = f"Привет, {user.username}!"
        role = "Админ панель доступна" if user.is_admin else ""
        self.role_hint = role


class AdminScreen(Screen):
    """Administrative overview of accounts."""

    summary = StringProperty("")

    def on_pre_enter(self, *args):  # type: ignore[override]
        app = App.get_running_app()
        self.summary = app.session_manager.all_accounts_summary()


class ChatScreen(Screen):
    """In-game chat activity."""

    chat_text = StringProperty("")

    def on_pre_enter(self, *args):  # type: ignore[override]
        self.refresh()

    def refresh(self) -> None:
        app = App.get_running_app()
        self.chat_text = app.session_manager.formatted_chat()

    def send_message(self) -> None:
        app = App.get_running_app()
        user = app.session_manager.active_user
        if not user:
            self.chat_text = "Только авторизованные игроки могут писать"
            return
        message = self.ids.chat_input.text
        app.session_manager.post_message(user.username, message)
        self.ids.chat_input.text = ""
        self.refresh()


class CharacterScreen(Screen):
    """Display character parameters."""

    stats = StringProperty("Авторизуйтесь, чтобы увидеть параметры")

    def on_pre_enter(self, *args):  # type: ignore[override]
        app = App.get_running_app()
        user = app.session_manager.active_user
        if not user:
            self.stats = "Авторизуйтесь, чтобы увидеть параметры"
            return
        char = user.character
        self.stats = (
            f"Имя: {char.name}\n"
            f"Уровень: {char.level}\n"
            f"Сила: {char.strength}\n"
            f"Выносливость: {int(char.stamina)}\n"
            f"Ярость: {int(char.rage)}\n"
            f"Добыча: {char.loot}\n"
            f"Скорость: {int(char.speed)}"
        )


class ArenaScreen(Screen):
    """Arena activity for quick fights."""

    result = StringProperty("Зайдите на арену и начните бой")

    def fight(self) -> None:
        app = App.get_running_app()
        try:
            self.result = app.session_manager.simulate_arena()
        except RuntimeError:
            self.result = "Сначала авторизуйтесь"


class ExpeditionScreen(Screen):
    """Manage expeditions."""

    status_message = StringProperty("")
    overview = StringProperty("")

    def on_pre_enter(self, *args):  # type: ignore[override]
        self.refresh()

    def refresh(self) -> None:
        app = App.get_running_app()
        expeditions = app.session_manager.available_expeditions()
        spinner = self.ids.expedition_spinner
        spinner.values = [exp.name for exp in expeditions]
        if spinner.values:
            spinner.text = spinner.values[0]
        self.overview = "\n".join(
            f"{exp.name}: {exp.difficulty}, статус — {exp.status}" for exp in expeditions
        )

    def start_selected(self) -> None:
        app = App.get_running_app()
        spinner = self.ids.expedition_spinner
        if not spinner.values:
            self.status_message = "Нет доступных экспедиций"
            return
        try:
            index = spinner.values.index(spinner.text)
        except ValueError:
            index = 0
        try:
            self.status_message = app.session_manager.start_expedition(index)
        except (ValueError, RuntimeError) as exc:
            self.status_message = str(exc)
        self.refresh()


class BossScreen(Screen):
    """Boss battle management."""

    status = StringProperty("")
    bosses_overview = StringProperty("")

    def on_pre_enter(self, *args):  # type: ignore[override]
        self.refresh()

    def refresh(self) -> None:
        app = App.get_running_app()
        spinner = self.ids.boss_spinner
        bosses = app.session_manager.bosses
        spinner.values = [boss.name for boss in bosses]
        if spinner.values:
            spinner.text = spinner.values[0]
        self.bosses_overview = app.session_manager.boss_summary()

    def challenge(self) -> None:
        app = App.get_running_app()
        spinner = self.ids.boss_spinner
        if not spinner.values:
            self.status = "Нет доступных боссов"
            return
        try:
            index = spinner.values.index(spinner.text)
        except ValueError:
            index = 0
        try:
            self.status = app.session_manager.challenge_boss(index)
        except (ValueError, RuntimeError) as exc:
            self.status = str(exc)
        self.refresh()


class WorldBoard(Widget):
    """Main gameplay widget with touch navigation."""

    game_state: GameState | None = ObjectProperty(None, rebind=True)  # type: ignore[assignment]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.clearcolor = (0.04, 0.05, 0.07, 1)
        self._objective_widgets: List[Tuple[Widget, Any]] = []
        Clock.schedule_interval(self._update, 1.0 / 60.0)

    def load_state(self, game_state: GameState | None = None) -> None:
        self.game_state = game_state or GameState.default()
        self._build_objective_markers()
        self._sync_ui()

    def _build_objective_markers(self) -> None:
        if not self.game_state:
            return
        for marker, _ in self._objective_widgets:
            if marker.parent is self:
                self.remove_widget(marker)
        self._objective_widgets.clear()

        for village in self.game_state.villages:
            marker = Factory.ObjectiveMarker()
            marker.size = (dp(28), dp(28))
            marker.pos = village.position
            marker.color = (0.3, 0.8, 0.5, 1)
            self._objective_widgets.append((marker, village))
            self.add_widget(marker, index=0)

        for camp in self.game_state.camps:
            marker = Factory.ObjectiveMarker()
            marker.size = (dp(32), dp(32))
            marker.pos = camp.position
            marker.color = (0.85, 0.3, 0.25, 1)
            self._objective_widgets.append((marker, camp))
            self.add_widget(marker, index=0)

        for cache in self.game_state.caches:
            marker = Factory.ObjectiveMarker()
            marker.size = (dp(24), dp(24))
            marker.pos = cache.position
            marker.color = (0.4, 0.7, 1.0, 1)
            self._objective_widgets.append((marker, cache))
            self.add_widget(marker, index=0)

    def on_touch_down(self, touch):  # type: ignore[override]
        if not self.collide_point(*touch.pos) or not self.game_state:
            return super().on_touch_down(touch)
        self.game_state.reset_destination(touch.pos)
        self.game_state.message = "Марш!"
        return True

    def _update(self, dt: float) -> None:
        if not self.game_state:
            return
        self.game_state.update(dt)
        self._sync_ui()
        if self.game_state.all_cleared():
            self.game_state.message = "Все земли освобождены!"

    def _sync_ui(self) -> None:
        if not self.game_state or "hero" not in self.ids:
            return
        hero = self.ids.hero
        hero.pos = self.game_state.barbarian.position

        for marker, entity in self._objective_widgets:
            if hasattr(entity, "defeated"):
                marker.opacity = 0.3 if entity.defeated else 1.0
            elif hasattr(entity, "liberated"):
                marker.opacity = 0.3 if entity.liberated else 1.0
            elif hasattr(entity, "taken"):
                marker.opacity = 0.3 if entity.taken else 1.0

        self.ids.message.text = self.game_state.message
        self.ids.stamina_bar.value = self.game_state.barbarian.stamina
        self.ids.rage_bar.value = self.game_state.barbarian.rage
        self.ids.level_label.text = f"Уровень {self.game_state.barbarian.level}"


class WorldScreen(Screen):
    """Screen embedding the interactive world map."""

    def on_pre_enter(self, *args):  # type: ignore[override]
        app = App.get_running_app()
        board: WorldBoard = self.ids.world_board
        try:
            state = app.session_manager.create_game_state()
        except RuntimeError:
            state = GameState.default()
        board.load_state(state)


class BarbarianApp(App):
    """Kivy application entry point."""

    session_manager: SessionManager

    def build(self):
        Window.size = (720, 520)
        self.session_manager = SessionManager()
        return RootManager()


if __name__ == "__main__":
    BarbarianApp().run()
