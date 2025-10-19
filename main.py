"""Flask entry point for the Barbarian Saga WAP MMORPG."""

from __future__ import annotations

import os
from typing import Optional

from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)

from barbarian_game import ARENA_OPPONENT, BOSSES, EXPEDITIONS, SessionManager, WORLD_MAP

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("BARBARIAN_SECRET_KEY", "dev-secret")

manager = SessionManager()


def current_player() -> Optional[str]:
    username = session.get("username")
    if not username:
        return None
    return username if manager.get_player(username) else None


@app.context_processor
def inject_globals():
    player = manager.get_player(session.get("username", "")) if "username" in session else None
    return {
        "world_map": WORLD_MAP,
        "expeditions": EXPEDITIONS,
        "bosses": BOSSES,
        "chat_log": manager.chat_log[-20:],
        "active_player": player,
        "arena_opponent": ARENA_OPPONENT,
    }


@app.get("/")
def index():
    username = current_player()
    if not username:
        return render_template("home.html")
    return redirect(url_for("dashboard"))


@app.post("/register")
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    try:
        manager.register(username, password)
        flash("Герой создан! Войдите, чтобы продолжить.")
    except ValueError as exc:
        flash(str(exc))
    return redirect(url_for("index"))


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    try:
        session_id = manager.authenticate(username, password)
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("index"))
    session["username"] = username
    session["session_id"] = session_id
    flash(f"Добро пожаловать, {username}!")
    return redirect(url_for("dashboard"))


@app.post("/logout")
def logout():
    session.clear()
    flash("Вы вышли из игры.")
    return redirect(url_for("index"))


def require_player():
    username = current_player()
    if not username:
        flash("Нужно войти в игру.")
        return None
    player = manager.get_player(username)
    if not player:
        flash("Профиль не найден.")
        return None
    return player


@app.get("/dashboard")
def dashboard():
    player = require_player()
    if not player:
        return redirect(url_for("index"))
    return render_template("dashboard.html", player=player)


@app.post("/chat")
def chat():
    player = require_player()
    if not player:
        return redirect(url_for("index"))
    message = request.form.get("message", "")
    try:
        manager.post_chat(player.username, message)
    except ValueError as exc:
        flash(str(exc))
    return redirect(url_for("dashboard"))


@app.post("/arena")
def arena():
    player = require_player()
    if not player:
        return redirect(url_for("index"))
    try:
        result = manager.resolve_arena_duel(player)
    except ValueError as exc:
        flash(str(exc))
    else:
        flash(result.message)
    return redirect(url_for("dashboard"))


@app.post("/expedition/<zone>")
def expedition(zone: str):
    player = require_player()
    if not player:
        return redirect(url_for("index"))
    try:
        result = manager.start_expedition(player, zone)
    except ValueError as exc:
        flash(str(exc))
    else:
        flash(result.message)
        if result.loot:
            flash(f"Получено: {result.loot.name} ({result.loot.rarity})")
    return redirect(url_for("dashboard"))


@app.post("/boss/<boss_key>")
def boss(boss_key: str):
    player = require_player()
    if not player:
        return redirect(url_for("index"))
    try:
        result = manager.challenge_boss(player, boss_key)
    except ValueError as exc:
        flash(str(exc))
    else:
        flash(result.message)
        if result.loot:
            flash(f"Получено: {result.loot.name} ({result.loot.rarity})")
    return redirect(url_for("dashboard"))


@app.post("/equip")
def equip():
    player = require_player()
    if not player:
        return redirect(url_for("index"))
    index = request.form.get("index")
    try:
        idx = int(index)
        item = player.inventory[idx]
        player.equip(item)
        flash(f"Экипирован предмет: {item.name}")
    except (ValueError, IndexError) as exc:
        flash("Не удалось экипировать предмет")
    return redirect(url_for("dashboard"))


@app.get("/admin")
def admin_panel():
    player = require_player()
    if not player:
        return redirect(url_for("index"))
    if player.role != "admin":
        flash("Недостаточно прав.")
        return redirect(url_for("dashboard"))
    overview = manager.list_players()
    return render_template("admin.html", players=overview)


if __name__ == "__main__":
    app.run(debug=True)
