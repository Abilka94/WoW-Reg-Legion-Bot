"""
Клавиатуры для пользователей — VK inline (callback_data → payload).
VK использует JSON-клавиатуру с массивом buttons и флагами inline/one_time.
"""
from ..config.settings import CONFIG
from ..config.translations import TRANSLATIONS as T


def _btn(label: str, payload: str, color: str = "primary"):
    """Создаёт callback-кнопку VK."""
    return {
        "action": {
            "type": "callback",
            "label": label,
            "payload": f'{{"cmd":"{payload}"}}',
        },
        "color": color,
    }


def _text_btn(label: str, payload: str, color: str = "primary"):
    """Создаёт текстовую кнопку VK (отправляет payload при нажатии)."""
    return {
        "action": {
            "type": "text",
            "label": label,
            "payload": f'{{"cmd":"{payload}"}}',
        },
        "color": color,
    }


def _inline_kb(rows: list[list[dict]]) -> dict:
    return {"inline": True, "buttons": rows}


def kb_main(is_admin: bool = False) -> dict:
    rows: list[list[dict]] = []
    if CONFIG["features"]["registration"]:
        rows.append([_btn(T["menu_reg"], "reg_start", "positive")])
    rows.append([
        _btn(T["menu_info"], "show_info", "primary"),
        _btn(T["menu_news"], "show_news", "primary"),
    ])
    if CONFIG["features"]["account_management"]:
        rows.append([_btn(T["menu_acc"], "my_account", "primary")])
    if is_admin:
        rows.append([_btn(T["menu_admin"], "open_admin_panel", "primary")])
    return _inline_kb(rows)


def kb_wizard(step: int) -> dict:
    btns: list[dict] = []
    if step > 0:
        btns.append(_btn(T["back"], "wiz_back", "primary"))
    btns.append(_btn(T["cancel"], "wiz_cancel", "negative"))
    return _inline_kb([btns])


def kb_back() -> dict:
    return _inline_kb([[_btn(T["to_main"], "back_to_main", "primary")]])


def kb_ok() -> dict:
    return _inline_kb([[_btn("OK", "error_ok", "secondary")]])


def kb_account_list(accounts, selected_email=None) -> dict:
    rows: list[list[dict]] = []
    for email, username, is_temp, temp_password in accounts:
        label = f"📧 {email}" + (" ✅" if email == selected_email else "")
        rows.append([_btn(label[:40], f"select_account_{email}", "secondary")])
    if selected_email and CONFIG["features"]["account_management"]:
        rows.append([_btn(T["menu_fgt"], f"reset_password_{selected_email}", "primary")])
        rows.append([_btn("🔄 Сменить пароль", f"change_password_{selected_email}", "primary")])
        rows.append([_btn("🗑 Удалить аккаунт", f"delete_account_{selected_email}", "negative")])
    rows.append([_btn(T["to_main"], "back_to_main", "primary")])
    return _inline_kb(rows)


def kb_password_weak_choice() -> dict:
    return _inline_kb([
        [
            _btn("✅ Использовать", "use_weak_password", "positive"),
            _btn("🔄 Другой", "change_weak_password", "primary"),
        ],
        [_btn(T["cancel"], "wiz_cancel", "negative")],
    ])


def kb_delete_confirm() -> dict:
    return _inline_kb([
        [
            _btn(T["admin_delete_confirm_yes"], "confirm_delete_yes", "negative"),
            _btn(T["admin_delete_confirm_no"], "confirm_delete_no", "primary"),
        ]
    ])
