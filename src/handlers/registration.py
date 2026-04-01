"""
Мастер регистрации — VK-версия.
Шаги: 1/3 ник → 2/3 пароль → 3/3 email.
"""
import logging
import pymysql

from ..config.settings import CONFIG, ADMIN_ID
from ..config.translations import TRANSLATIONS as T
from ..states import user_states as S
from ..keyboards.user_keyboards import kb_main, kb_wizard, kb_ok, kb_password_weak_choice
from ..utils.notifications import record_message, delete_all_bot_messages, safe_send_or_edit
from ..utils.validators import validate_nickname, validate_password, validate_email, check_password_strength
from ..database.user_operations import register_user

logger = logging.getLogger("bot")

user_wizard_msg: dict[int, int | None] = {}


async def handle_callback(api, pool, user_id, peer_id, cmd, fsm, event_id, conv_msg_id):
    """Обрабатывает callback'и регистрации. Возвращает True если обработано."""

    if cmd == "reg_start":
        if not CONFIG["features"]["registration"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        await ctx.set_state(S.REG_NICK)
        text = f"1/3 · {T['progress'][0]}"
        mid = await safe_send_or_edit(api, peer_id, text, kb_wizard(0), conv_msg_id)
        user_wizard_msg[user_id] = mid
        record_message(user_id, mid, "conversation")
        await api.send_event_answer(event_id, user_id, peer_id)
        logger.info(f"Начало регистрации vk_id={user_id}")
        return True

    if cmd in ("wiz_back", "wiz_cancel"):
        ctx = fsm.get_context(user_id)
        cur = await ctx.get_state()

        if cmd == "wiz_cancel":
            await ctx.clear()
            await delete_all_bot_messages(user_id, api)
            mid = await api.send_message(peer_id, T["start"], kb_main(is_admin=user_id == ADMIN_ID))
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True

        if cur == S.REG_NICK:
            await ctx.clear()
            await delete_all_bot_messages(user_id, api)
            mid = await api.send_message(peer_id, T["start"], kb_main(is_admin=user_id == ADMIN_ID))
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True

        if cur == S.REG_PWD:
            await ctx.set_state(S.REG_NICK)
            text = f"1/3 · {T['progress'][0]}"
            mid = await safe_send_or_edit(api, peer_id, text, kb_wizard(0), user_wizard_msg.get(user_id))
            user_wizard_msg[user_id] = mid
            await api.send_event_answer(event_id, user_id, peer_id)
            return True

        if cur == S.REG_MAIL:
            await ctx.set_state(S.REG_PWD)
            text = f"2/3 · {T['progress'][1]}"
            mid = await safe_send_or_edit(api, peer_id, text, kb_wizard(1), user_wizard_msg.get(user_id))
            user_wizard_msg[user_id] = mid
            await api.send_event_answer(event_id, user_id, peer_id)
            return True

        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "use_weak_password":
        ctx = fsm.get_context(user_id)
        cur = await ctx.get_state()
        if cur == S.REG_PWD_WEAK:
            await ctx.set_state(S.REG_MAIL)
            text = f"3/3 · {T['progress'][2]}"
            mid = await safe_send_or_edit(api, peer_id, text, kb_wizard(2), user_wizard_msg.get(user_id))
            user_wizard_msg[user_id] = mid
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        return False

    if cmd == "change_weak_password":
        ctx = fsm.get_context(user_id)
        cur = await ctx.get_state()
        if cur == S.REG_PWD_WEAK:
            await ctx.set_state(S.REG_PWD)
            text = f"2/3 · {T['progress'][1]}"
            mid = await safe_send_or_edit(api, peer_id, text, kb_wizard(1), user_wizard_msg.get(user_id))
            user_wizard_msg[user_id] = mid
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        return False

    return False


async def handle_text(api, pool, user_id, peer_id, text, fsm, msg_id):
    """Обрабатывает текстовый ввод на шагах регистрации. Возвращает True если обработано."""
    ctx = fsm.get_context(user_id)
    cur = await ctx.get_state()

    if cur == S.REG_NICK:
        if text.startswith("/"):
            await ctx.clear()
            return False

        if len(text) > 50 or " " in text or not text:
            await ctx.clear()
            await _try_delete(api, peer_id, msg_id)
            mid = await api.send_message(peer_id, T["start"], kb_main(is_admin=user_id == ADMIN_ID))
            record_message(user_id, mid, "command")
            return True

        if not validate_nickname(text):
            mid = await api.send_message(peer_id, T["err_nick"], kb_ok())
            record_message(user_id, mid, "error")
            await _try_delete(api, peer_id, msg_id)
            return True

        await ctx.update_data(nick=text)
        await ctx.set_state(S.REG_PWD)
        step_text = f"2/3 · {T['progress'][1]}"
        mid = await safe_send_or_edit(api, peer_id, step_text, kb_wizard(1), user_wizard_msg.get(user_id))
        user_wizard_msg[user_id] = mid
        await _try_delete(api, peer_id, msg_id)
        return True

    if cur == S.REG_PWD:
        if text.startswith("/"):
            await ctx.clear()
            return False

        if len(text) > 100 or not text:
            await ctx.clear()
            await _try_delete(api, peer_id, msg_id)
            mid = await api.send_message(peer_id, T["start"], kb_main(is_admin=user_id == ADMIN_ID))
            record_message(user_id, mid, "command")
            return True

        is_valid, error_msg = validate_password(text)
        if not is_valid:
            mid = await api.send_message(peer_id, f"❌ {error_msg}", kb_ok())
            record_message(user_id, mid, "error")
            await _try_delete(api, peer_id, msg_id)
            return True

        is_strong, warning_msg = check_password_strength(text)
        if not is_strong:
            await ctx.update_data(pwd=text)
            await ctx.set_state(S.REG_PWD_WEAK)
            warning_text = T["password_weak_warning"].format(warning=warning_msg)
            mid = await safe_send_or_edit(api, peer_id, warning_text, kb_password_weak_choice(), user_wizard_msg.get(user_id))
            user_wizard_msg[user_id] = mid
            await _try_delete(api, peer_id, msg_id)
            return True

        await ctx.update_data(pwd=text)
        await ctx.set_state(S.REG_MAIL)
        step_text = f"3/3 · {T['progress'][2]}"
        mid = await safe_send_or_edit(api, peer_id, step_text, kb_wizard(2), user_wizard_msg.get(user_id))
        user_wizard_msg[user_id] = mid
        await _try_delete(api, peer_id, msg_id)
        return True

    if cur == S.REG_MAIL:
        if text.startswith("/"):
            await ctx.clear()
            return False

        if len(text) > 254 or not text:
            await ctx.clear()
            await _try_delete(api, peer_id, msg_id)
            mid = await api.send_message(peer_id, T["start"], kb_main(is_admin=user_id == ADMIN_ID))
            record_message(user_id, mid, "command")
            return True

        is_valid, error_msg = validate_email(text, strict=True)
        if not is_valid:
            mid = await api.send_message(peer_id, f"❌ {error_msg}\n\n{T['err_mail']}", kb_ok())
            record_message(user_id, mid, "error")
            await _try_delete(api, peer_id, msg_id)
            return True

        data = await ctx.get_data()
        try:
            login, error = await register_user(pool, data["nick"], data["pwd"], text, user_id)
            await ctx.clear()
            await delete_all_bot_messages(user_id, api)

            if login:
                mid = await api.send_message(peer_id, T["success"].format(username=login), kb_main(is_admin=user_id == ADMIN_ID))
            else:
                err_text = T[error].format(max_accounts=CONFIG["settings"]["max_accounts_per_user"])
                mid = await api.send_message(peer_id, err_text, kb_main(is_admin=user_id == ADMIN_ID))
            record_message(user_id, mid, "command")
        except pymysql.err.IntegrityError as e:
            logger.error(f"IntegrityError при регистрации {text}: {e}")
            await ctx.clear()
            await delete_all_bot_messages(user_id, api)
            mid = await api.send_message(peer_id, T["err_exists"], kb_main(is_admin=user_id == ADMIN_ID))
            record_message(user_id, mid, "command")

        await _try_delete(api, peer_id, msg_id)
        return True

    return False


async def _try_delete(api, peer_id, msg_id):
    if msg_id:
        try:
            await api.delete_message(peer_id, msg_id)
        except Exception:
            pass
