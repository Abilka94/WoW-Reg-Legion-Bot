"""
Клавиатуры для администратора — VK
"""
from ..config.settings import CONFIG
from ..config.translations import TRANSLATIONS as T


def _btn(label: str, payload: str, color: str = "primary"):
    return {
        "action": {
            "type": "callback",
            "label": label,
            "payload": f'{{"cmd":"{payload}"}}',
        },
        "color": color,
    }


def _inline_kb(rows):
    return {"inline": True, "buttons": rows}


def kb_admin() -> dict:
    rows = []
    if CONFIG["features"]["admin_check_db"]:
        rows.append([_btn(T["admin_db"], "admin_check_db", "positive")])
    if CONFIG["features"]["admin_broadcast"]:
        rows.append([_btn(T["admin_bcast"], "admin_broadcast", "primary")])
    if CONFIG["features"]["admin_delete_account"]:
        rows.append([_btn(T["admin_delete_account"], "admin_delete_account", "negative")])
    if CONFIG["features"]["admin_reload_config"]:
        rows.append([_btn(T["admin_reload_config"], "admin_reload_config", "primary")])
    rows.append([_btn(T["admin_main"], "admin_main", "secondary")])
    return _inline_kb(rows)


def kb_admin_back() -> dict:
    return _inline_kb([[_btn(T["admin_back"], "admin_back", "primary")]])
