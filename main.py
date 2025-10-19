"""Barbarian Saga – a mobile friendly Kivy prototype."""

from __future__ import annotations

from pathlib import Path
from random import randint
from typing import Any, List, Tuple

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.widget import Widget

from barbarian_game import Barbarian, EnemyCamp, GameState, ResourceCache, Village

ASSETS_DIR = Path(__file__).parent / "barbarian_game"
Builder.load_file(str(ASSETS_DIR / "barbarian.kv"))


def _build_default_state() -> GameState:
    barbarian = Barbarian(position=(120.0, 160.0), destination=(320.0, 240.0))
    villages = [
        Village("Долина", (90.0, 360.0), prosperity=25),
        Village("Ветряное", (420.0, 120.0), prosperity=30),
    ]
    camps = [
        EnemyCamp("Лагерь клана", (320.0, 420.0), strength=3, loot=25),
        EnemyCamp("Темный форпост", (520.0, 260.0), strength=5, loot=45, enrages_on_attack=True),
        EnemyCamp("Арена вожака", (140.0, 120.0), strength=7, loot=60),
    ]
    caches = [
        ResourceCache((randint(140, 480), randint(140, 380)), amount=35.0),
        ResourceCache((randint(80, 520), randint(80, 440)), amount=25.0),
    ]
    return GameState(barbarian=barbarian, villages=villages, camps=camps, caches=caches)


class GameScreen(Widget):
    """Main gameplay widget."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.clearcolor = (0.04, 0.05, 0.07, 1)
        self.game_state = _build_default_state()
        self._objective_widgets: List[Tuple[Widget, Any]] = []
        self._build_objective_markers()
        Clock.schedule_interval(self._update, 1.0 / 60.0)

    def _build_objective_markers(self) -> None:
        for marker, _ in self._objective_widgets:
            self.remove_widget(marker)
        self._objective_widgets.clear()

        for village in self.game_state.villages:
            marker = Factory.ObjectiveMarker()
            marker.size = (dp(28), dp(28))
            marker.pos = village.position
            marker.color = (0.3, 0.8, 0.5, 1)
            self._objective_widgets.append((marker, village))
            self.add_widget(marker)

        for camp in self.game_state.camps:
            marker = Factory.ObjectiveMarker()
            marker.size = (dp(32), dp(32))
            marker.pos = camp.position
            marker.color = (0.85, 0.3, 0.25, 1)
            self._objective_widgets.append((marker, camp))
            self.add_widget(marker)

        for cache in self.game_state.caches:
            marker = Factory.ObjectiveMarker()
            marker.size = (dp(24), dp(24))
            marker.pos = cache.position
            marker.color = (0.4, 0.7, 1.0, 1)
            self._objective_widgets.append((marker, cache))
            self.add_widget(marker)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        self.game_state.reset_destination(touch.pos)
        self.game_state.message = "Марш!"
        return True

    def _update(self, dt: float) -> None:
        self.game_state.update(dt)
        self._sync_ui()
        if self.game_state.all_cleared():
            self.game_state.message = "Все земли освобождены!"

    def _sync_ui(self) -> None:
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


class BarbarianApp(App):
    """Kivy application entry point."""

    def build(self):
        Window.size = (640, 480)
        return GameScreen()


if __name__ == "__main__":
    BarbarianApp().run()
