"""
Управление аккаунтами — VK-версия.
Просмотр, сброс пароля, смена пароля, удаление.
"""
import logging

from ..config.settings import CONFIG, ADMIN_ID
from ..config.translations import TRANSLATIONS as T
from ..states import user_states as S
from ..keyboards.user_keyboards import (
    kb_main, kb_back, kb_account_list, kb_ok, kb_password_weak_choice, kb_delete_confirm,
)
from ..utils.notifications import record_message, delete_all_bot_messages, safe_send_or_edit
from ..utils.validators import validate_password, check_password_strength
from ..database.user_operations import reset_password, change_password, get_account_info, delete_account

logger = logging.getLogger("bot")


async def handle_callback(api, pool, user_id, peer_id, cmd, fsm, event_id, conv_msg_id):
    """Callback-обработчики для раздела «Мой аккаунт»."""

    if cmd == "my_account":
        if not CONFIG["features"]["account_management"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        accounts = await get_account_info(pool, user_id)
        if not accounts:
            mid = await api.send_message(peer_id, T["account_no_account"], kb_back())
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        mid = await api.send_message(peer_id, T["select_account_prompt"], kb_account_list(accounts))
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd.startswith("select_account_"):
        if not CONFIG["features"]["account_management"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        email = cmd.replace("select_account_", "")
        accounts = await get_account_info(pool, user_id)
        if not accounts:
            mid = await api.send_message(peer_id, T["account_no_account"], kb_back())
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        selected = next((a for a in accounts if a[0] == email), None)
        if not selected:
            mid = await api.send_message(peer_id, T["no_access"], kb_back())
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        email, username, is_temp, temp_password = selected
        pwd_status = T["reset_success"].format(password=temp_password) if is_temp else T["change_password_success"]
        text = T["account_info"].format(username=username, email=email, password_status=pwd_status)
        mid = await safe_send_or_edit(api, peer_id, text, kb_account_list(accounts, selected_email=email), conv_msg_id)
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd.startswith("reset_password_"):
        if not CONFIG["features"]["account_management"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        email = cmd.replace("reset_password_", "")
        accounts = await get_account_info(pool, user_id)
        if not any(a[0] == email for a in accounts):
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": "❌ Нет доступа"})
            return True
        tmp = await reset_password(pool, email)
        if tmp is None:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["reset_err_not_found"]})
            return True
        text = T["reset_success"].format(password=tmp)
        mid = await safe_send_or_edit(api, peer_id, text, kb_account_list(accounts, selected_email=email), conv_msg_id)
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd.startswith("change_password_"):
        if not CONFIG["features"]["account_management"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        email = cmd.replace("change_password_", "")
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        accounts = await get_account_info(pool, user_id)
        if not accounts or not any(a[0] == email for a in accounts):
            mid = await api.send_message(peer_id, T["account_no_account"], kb_back())
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        await ctx.set_state(S.CHANGE_PWD)
        await ctx.update_data(email=email)
        mid = await api.send_message(peer_id, T["change_password_prompt"], kb_back())
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd.startswith("delete_account_"):
        if not CONFIG["features"]["account_management"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        email = cmd.replace("delete_account_", "")
        accounts = await get_account_info(pool, user_id)
        selected = next((a for a in accounts if a[0] == email), None)
        if not selected:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["delete_account_error"]})
            return True
        email_s, username, _, _ = selected
        ctx = fsm.get_context(user_id)
        await ctx.update_data(delete_email=email_s, delete_username=username)
        await ctx.set_state(S.USER_DELETE_CONFIRM)
        text = T["admin_delete_confirm"].format(email=email_s, username=username)
        mid = await safe_send_or_edit(api, peer_id, text, kb_delete_confirm(), conv_msg_id)
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "confirm_delete_yes":
        ctx = fsm.get_context(user_id)
        data = await ctx.get_data()
        email = data.get("delete_email")
        if not email:
            await ctx.clear()
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["delete_account_error"]})
            return True
        success = await delete_account(pool, user_id, email)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        if not success:
            mid = await api.send_message(peer_id, T["delete_account_error"], kb_back())
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        accounts = await get_account_info(pool, user_id)
        if not accounts:
            mid = await api.send_message(peer_id, T["delete_account_success"] + "\n\n" + T["account_no_account"], kb_back())
        else:
            mid = await api.send_message(peer_id, T["delete_account_success"] + "\n\n" + T["select_account_prompt"], kb_account_list(accounts))
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "confirm_delete_no":
        ctx = fsm.get_context(user_id)
        data = await ctx.get_data()
        email = data.get("delete_email")
        await ctx.clear()
        accounts = await get_account_info(pool, user_id)
        selected = next((a for a in (accounts or []) if a[0] == email), None) if email else None
        if selected and accounts:
            e, u, it, tp = selected
            pwd_st = T["reset_success"].format(password=tp) if it else T["change_password_success"]
            text = T["account_info"].format(username=u, email=e, password_status=pwd_st)
            mid = await safe_send_or_edit(api, peer_id, text, kb_account_list(accounts, selected_email=e), conv_msg_id)
        else:
            mid = await api.send_message(peer_id, T["select_account_prompt"], kb_account_list(accounts or []))
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    # use_weak_password / change_weak_password для смены пароля
    if cmd == "use_weak_password":
        ctx = fsm.get_context(user_id)
        cur = await ctx.get_state()
        if cur == S.CHANGE_PWD_WEAK:
            data = await ctx.get_data()
            new_password = data.get("new_password")
            email = data.get("email")
            try:
                await change_password(pool, email, new_password)
                await ctx.clear()
                await delete_all_bot_messages(user_id, api)
                mid = await api.send_message(peer_id, T["change_password_success"], kb_main(is_admin=user_id == ADMIN_ID))
                record_message(user_id, mid, "command")
            except Exception as e:
                logger.error(f"Ошибка смены пароля: {e}")
                await ctx.clear()
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        return False

    if cmd == "change_weak_password":
        ctx = fsm.get_context(user_id)
        cur = await ctx.get_state()
        if cur == S.CHANGE_PWD_WEAK:
            await ctx.set_state(S.CHANGE_PWD)
            mid = await safe_send_or_edit(api, peer_id, T["change_password_prompt"], kb_back(), conv_msg_id)
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        return False

    return False


async def handle_text(api, pool, user_id, peer_id, text, fsm, msg_id):
    """Обработка текстового ввода в контексте управления аккаунтом."""
    ctx = fsm.get_context(user_id)
    cur = await ctx.get_state()

    if cur == S.CHANGE_PWD:
        if text in (T["to_main"], T["cancel"]):
            await ctx.clear()
            mid = await api.send_message(peer_id, T["start"], kb_main(is_admin=user_id == ADMIN_ID))
            record_message(user_id, mid, "command")
            await _try_delete(api, peer_id, msg_id)
            return True

        data = await ctx.get_data()
        email = data.get("email")

        is_valid, error_msg = validate_password(text)
        if not is_valid:
            mid = await api.send_message(peer_id, f"❌ {error_msg}", kb_ok())
            record_message(user_id, mid, "error")
            await _try_delete(api, peer_id, msg_id)
            return True

        is_strong, warning_msg = check_password_strength(text)
        if not is_strong:
            await ctx.update_data(new_password=text)
            await ctx.set_state(S.CHANGE_PWD_WEAK)
            warning_text = T["password_weak_warning"].format(warning=warning_msg)
            mid = await api.send_message(peer_id, warning_text, kb_password_weak_choice())
            record_message(user_id, mid, "conversation")
            await _try_delete(api, peer_id, msg_id)
            return True

        await change_password(pool, email, text)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        mid = await api.send_message(peer_id, T["change_password_success"], kb_main(is_admin=user_id == ADMIN_ID))
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
