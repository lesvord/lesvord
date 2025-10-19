"""Entry point for the Barbarian Saga WAP MMORPG without third-party deps."""

from __future__ import annotations

from typing import Iterable, List, Optional

from barbarian_game import ARENA_OPPONENT, BOSSES, EXPEDITIONS, SessionManager, WORLD_MAP
from barbarian_game.miniapp import MiniApp, flash, pop_flashes, redirect, request, session
from barbarian_game.models import Item, Player

app = MiniApp("barbarian_saga")
app.config["SECRET_KEY"] = "dev-secret"

manager = SessionManager()


# --------------------------------------------------------------------------- helpers

def current_player() -> Optional[Player]:
    username = session.get("username") if "username" in session else None
    if not username:
        return None
    return manager.get_player(username)


def require_player() -> Optional[Player]:
    player = current_player()
    if player is None:
        flash("Нужно войти в игру.")
    return player


def render_layout(title: str, sections: Iterable[str], player: Optional[Player] = None) -> str:
    flashes = pop_flashes()
    nav_parts: List[str] = ["<a href='/'>Главная</a>"]
    if player:
        nav_parts.append("<a href='/dashboard'>Панель героя</a>")
        if player.role == "admin":
            nav_parts.append("<a href='/admin'>Совет клана</a>")
        nav_parts.append(
            "<form method='post' action='/logout' style='display:inline'>"
            "<button type='submit'>Выход</button></form>"
        )
        user_label = f"<span class='badge'>Герой: {player.username}</span>"
    else:
        nav_parts.append("<span>Гость клана</span>")
        user_label = ""
    nav_html = "<nav>" + " | ".join(nav_parts) + user_label + "</nav>"

    flash_html = ""
    if flashes:
        flash_items = "".join(f"<li>{msg}</li>" for msg in flashes)
        flash_html = f"<div class='flash'><ul>{flash_items}</ul></div>"

    content = "".join(f"<section class='panel'>{section}</section>" for section in sections)
    return (
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'>"
        f"<title>{title}</title>"
        "<style>body{font-family:Arial,sans-serif;background:#111;color:#f4f4f4;margin:0;padding:1rem;}"
        "a{color:#ffcc66;}nav{margin-bottom:1rem;}nav .badge{margin-left:1rem;color:#ffcc66;}"
        "button,input[type=submit]{background:#c44;color:#fff;border:none;padding:0.4rem 0.8rem;margin-top:0.4rem;}"
        "form{margin-top:0.4rem;}pre.map{background:#222;padding:0.6rem;overflow:auto;}"
        ".panel{background:#1a1a1a;padding:0.8rem;margin-bottom:1rem;border:1px solid #333;}"
        "table{width:100%;border-collapse:collapse;}th,td{border:1px solid #333;padding:0.3rem;text-align:left;}"
        "ul{list-style:none;padding-left:0;}li{margin:0.2rem 0;}"
        ".flash{background:#332208;border:1px solid #aa7f39;padding:0.4rem;margin-bottom:1rem;}"
        "</style></head><body>"
        f"<header><h1>Barbarian Saga · WAP</h1>{nav_html}</header>"
        f"{flash_html}{content}</body></html>"
    )


def render_home() -> str:
    sections = [
        f"<h2>Столица клана</h2><pre class='map'>{WORLD_MAP}</pre>",
        "<h3>Создать героя</h3>"
        "<form method='post' action='/register'>"
        "<label>Имя: <input name='username' required></label><br>"
        "<label>Пароль: <input type='password' name='password' required></label><br>"
        "<input type='submit' value='Регистрация'>"
        "</form>",
        "<h3>Войти</h3>"
        "<form method='post' action='/login'>"
        "<label>Имя: <input name='username' required></label><br>"
        "<label>Пароль: <input type='password' name='password' required></label><br>"
        "<input type='submit' value='Войти в клан'>"
        "</form>",
    ]
    return render_layout("Barbarian Saga - вход", sections)


def render_stats_table(player: Player) -> str:
    base = player.stats.as_dict()
    total = player.total_stats().as_dict()
    rows = "".join(
        f"<tr><td>{name}</td><td>{base[name]}</td><td>{total[name]}</td></tr>" for name in base
    )
    return (
        f"<h2>{player.username} — уровень {player.level}</h2>"
        f"<p>Энергия: {player.energy} / 120 · Золото: {player.gold} · Репутация: {player.reputation}</p>"
        "<table><thead><tr><th>Характеристика</th><th>Базово</th><th>Итого</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def render_equipment(player: Player) -> str:
    if not player.equipment:
        return "<h3>Экипировка</h3><p>Пока ничего не экипировано.</p>"
    items = "".join(
        f"<li><strong>{slot}</strong>: {item.name} (сил.{item.power}, {item.rarity})</li>"
        for slot, item in player.equipment.items()
    )
    return f"<h3>Экипировка</h3><ul>{items}</ul>"


def render_inventory(player: Player) -> str:
    if not player.inventory:
        return "<h3>Инвентарь</h3><p>Инвентарь пуст — отправляйтесь в экспедицию!</p>"
    entries = []
    for idx, item in enumerate(player.inventory):
        entries.append(
            "<li>"
            f"{item.name} — слот {item.slot}, сила {item.power}"
            "<form method='post' action='/equip'>"
            f"<input type='hidden' name='index' value='{idx}'>"
            "<input type='submit' value='Экипировать'>"
            "</form>"
            "</li>"
        )
    return "<h3>Инвентарь</h3><ul>" + "".join(entries) + "</ul>"


def render_chat() -> str:
    messages = manager.chat_log[-20:]
    if messages:
        items = "".join(f"<li><strong>{m.username}</strong>: {m.text}</li>" for m in messages)
    else:
        items = "<li>Пока нет сообщений.</li>"
    return (
        "<h3>Клановый чат</h3>"
        f"<ul>{items}</ul>"
        "<form method='post' action='/chat'>"
        "<input type='text' name='message' placeholder='Передать привет клану' required>"
        "<input type='submit' value='Отправить'>"
        "</form>"
    )


def render_arena() -> str:
    opponent = ARENA_OPPONENT
    return (
        "<h3>Арена</h3>"
        f"<p>Соперник: {opponent['name']} · Мощь: {opponent['power']} · Энергия: 12</p>"
        "<form method='post' action='/arena'>"
        "<input type='submit' value='Вызвать на бой'>"
        "</form>"
    )


def render_expeditions() -> str:
    parts = []
    for key, zone in EXPEDITIONS.items():
        parts.append(
            "<li>"
            f"<strong>{zone['title']}</strong>: сложность {zone['difficulty']}, энергия {zone['energy']}, "
            f"награда {zone['gold']} золота / {zone['xp']} опыта."
            "<form method='post' action='/expedition/" + key + "'>"
            "<input type='submit' value='Отправиться'>"
            "</form>"
            "</li>"
        )
    return "<h3>Экспедиции</h3><ul>" + "".join(parts) + "</ul>"


def render_bosses() -> str:
    parts = []
    for key, boss in BOSSES.items():
        reward: Item = boss["reward"]
        parts.append(
            "<li>"
            f"<strong>{boss['title']}</strong>: требуемая мощь {boss['threshold']}, энергия {boss['energy']}. "
            f"Трофей — {reward.name}."
            "<form method='post' action='/boss/" + key + "'>"
            "<input type='submit' value='Сразиться'>"
            "</form>"
            "</li>"
        )
    return "<h3>Боссы</h3><ul>" + "".join(parts) + "</ul>"


def render_dashboard(player: Player) -> str:
    sections = [
        f"<h2>Карта мира</h2><pre class='map'>{WORLD_MAP}</pre>",
        render_stats_table(player),
        render_equipment(player),
        render_inventory(player),
        render_chat(),
        render_arena(),
        render_expeditions(),
        render_bosses(),
    ]
    return render_layout("Barbarian Saga - панель героя", sections, player)


def render_admin_panel(player: Player) -> str:
    overview = manager.list_players()
    rows = []
    for hero in overview:
        equipment = ", ".join(f"{item['slot']}: {item['item']['name']}" for item in hero["equipment"]) or "—"
        rows.append(
            "<tr>"
            f"<td>{hero['username']}</td>"
            f"<td>{hero['level']}</td>"
            f"<td>{hero['gold']}</td>"
            f"<td>{hero['reputation']}</td>"
            f"<td>{equipment}</td>"
            "</tr>"
        )
    header = (
        "<table><thead><tr>"
        "<th>Герой</th><th>Уровень</th><th>Золото</th><th>Репутация</th><th>Экипировка</th>"
        "</tr></thead>"
    )
    table = "<h2>Совет клана</h2>" + header + f"<tbody>{''.join(rows)}</tbody></table>"
    sections = [table]
    return render_layout("Barbarian Saga - администрирование", sections, player)


# --------------------------------------------------------------------------- routes


@app.get("/")
def index():
    player = current_player()
    if not player:
        return app.make_response(render_home())
    return redirect("/dashboard")


@app.post("/register")
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    try:
        manager.register(username, password)
        flash("Герой создан! Войдите, чтобы продолжить.")
    except ValueError as exc:
        flash(str(exc))
    return redirect("/")


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    try:
        session_id = manager.authenticate(username, password)
    except ValueError as exc:
        flash(str(exc))
        return redirect("/")
    session["username"] = username
    session["session_id"] = session_id
    flash(f"Добро пожаловать, {username}!")
    return redirect("/dashboard")


@app.post("/logout")
def logout():
    session.clear()
    flash("Вы вышли из игры.")
    return redirect("/")


@app.get("/dashboard")
def dashboard():
    player = require_player()
    if not player:
        return redirect("/")
    return app.make_response(render_dashboard(player))


@app.post("/chat")
def chat():
    player = require_player()
    if not player:
        return redirect("/")
    message = request.form.get("message", "")
    try:
        manager.post_chat(player.username, message)
    except ValueError as exc:
        flash(str(exc))
    return redirect("/dashboard")


@app.post("/arena")
def arena():
    player = require_player()
    if not player:
        return redirect("/")
    try:
        result = manager.resolve_arena_duel(player)
    except ValueError as exc:
        flash(str(exc))
    else:
        flash(result.message)
    return redirect("/dashboard")


@app.post("/expedition/<zone>")
def expedition(zone: str):
    player = require_player()
    if not player:
        return redirect("/")
    try:
        result = manager.start_expedition(player, zone)
    except ValueError as exc:
        flash(str(exc))
    else:
        flash(result.message)
        if result.loot:
            flash(f"Получено: {result.loot.name} ({result.loot.rarity})")
    return redirect("/dashboard")


@app.post("/boss/<boss_key>")
def boss(boss_key: str):
    player = require_player()
    if not player:
        return redirect("/")
    try:
        result = manager.challenge_boss(player, boss_key)
    except ValueError as exc:
        flash(str(exc))
    else:
        flash(result.message)
        if result.loot:
            flash(f"Получено: {result.loot.name} ({result.loot.rarity})")
    return redirect("/dashboard")


@app.post("/equip")
def equip():
    player = require_player()
    if not player:
        return redirect("/")
    index_value = request.form.get("index", "")
    try:
        idx = int(index_value)
        item = player.inventory[idx]
        player.equip(item)
        flash(f"Экипирован предмет: {item.name}")
    except (ValueError, IndexError):
        flash("Не удалось экипировать предмет")
    return redirect("/dashboard")


@app.get("/admin")
def admin_panel():
    player = require_player()
    if not player:
        return redirect("/")
    if player.role != "admin":
        flash("Недостаточно прав.")
        return redirect("/dashboard")
    return app.make_response(render_admin_panel(player))


if __name__ == "__main__":
    app.serve()
