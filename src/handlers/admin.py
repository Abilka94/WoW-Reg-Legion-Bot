"""
Административные обработчики — VK-версия.
Проверка БД, рассылка, удаление аккаунта, перезагрузка конфига.
"""
import logging

from ..config.settings import CONFIG, ADMIN_ID
from ..config.translations import TRANSLATIONS as T
from ..states import user_states as S
from ..keyboards.user_keyboards import kb_main, kb_back
from ..keyboards.admin_keyboards import kb_admin, kb_admin_back
from ..utils.notifications import record_message, delete_all_bot_messages, safe_send_or_edit, notify_admin
from ..utils.validators import validate_email
from ..database.user_operations import admin_delete_account, get_account_by_email, get_all_user_ids

logger = logging.getLogger("bot")


async def handle_callback(api, pool, user_id, peer_id, cmd, fsm, event_id, conv_msg_id):

    if cmd == "admin_check_db":
        if not CONFIG["features"]["admin_check_db"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        if user_id != ADMIN_ID:
            mid = await api.send_message(peer_id, T["no_access"], kb_back())
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        try:
            async with pool.acquire():
                pass
            txt = T["db_ok"]
        except Exception as e:
            txt = f"❌ {e}"
            await notify_admin(api, ADMIN_ID, str(e))
            logger.error(f"Ошибка проверки БД: {e}")
        mid = await api.send_message(peer_id, txt, kb_admin_back())
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "admin_broadcast":
        if not CONFIG["features"]["admin_broadcast"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        if user_id != ADMIN_ID:
            mid = await api.send_message(peer_id, T["no_access"], kb_back())
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        await ctx.set_state(S.ADMIN_BROADCAST)
        mid = await api.send_message(peer_id, "Введите текст рассылки:", kb_admin_back())
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "admin_delete_account":
        if not CONFIG["features"]["admin_delete_account"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        if user_id != ADMIN_ID:
            mid = await api.send_message(peer_id, T["no_access"], kb_back())
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        await ctx.set_state(S.ADMIN_DELETE_INPUT)
        mid = await api.send_message(peer_id, T["admin_delete_prompt"], kb_admin_back())
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "admin_confirm_delete":
        if user_id != ADMIN_ID:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["no_access"]})
            return True
        ctx = fsm.get_context(user_id)
        data = await ctx.get_data()
        email = data.get("email")
        username = data.get("username")
        if not email:
            await ctx.clear()
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": "❌ Данные не найдены"})
            mid = await safe_send_or_edit(api, peer_id, T["admin_panel"], kb_admin(), conv_msg_id)
            record_message(user_id, mid, "command")
            return True
        try:
            success, deleted_vk_id = await admin_delete_account(pool, email)
            await ctx.clear()
            if success:
                if deleted_vk_id:
                    try:
                        notification_text = T["account_deleted_by_admin"].format(email=email, username=username)
                        await api.send_message(deleted_vk_id, notification_text)
                        logger.info(f"Уведомление отправлено vk_id {deleted_vk_id}")
                    except Exception as e:
                        logger.warning(f"Не удалось уведомить vk_id {deleted_vk_id}: {e}")
                mid = await safe_send_or_edit(api, peer_id, T["admin_delete_success"].format(email=email), kb_admin_back(), conv_msg_id)
            else:
                mid = await safe_send_or_edit(api, peer_id, T["admin_delete_error"].format(error="Не удалось удалить"), kb_admin_back(), conv_msg_id)
            record_message(user_id, mid, "command")
        except Exception as e:
            logger.error(f"Ошибка при удалении аккаунта админом: {e}")
            await ctx.clear()
            mid = await safe_send_or_edit(api, peer_id, T["admin_delete_error"].format(error=str(e)), kb_admin_back(), conv_msg_id)
            record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "admin_reload_config":
        if not CONFIG["features"]["admin_reload_config"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        if user_id != ADMIN_ID:
            mid = await api.send_message(peer_id, T["no_access"], kb_back())
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        try:
            from ..config.settings import load_config
            load_config()
            mid = await api.send_message(peer_id, T["reload_config_success"], kb_admin())
        except Exception as e:
            logger.error(f"Ошибка перезагрузки конфига: {e}")
            mid = await api.send_message(peer_id, T["reload_config_error"].format(error=str(e)), kb_admin())
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    return False


async def handle_text(api, pool, user_id, peer_id, text, fsm, msg_id):
    """Текстовый ввод для административных состояний."""
    ctx = fsm.get_context(user_id)
    cur = await ctx.get_state()

    if cur == S.ADMIN_BROADCAST:
        if text.strip() in (T["cancel"], T["admin_back"]):
            await ctx.clear()
            await delete_all_bot_messages(user_id, api)
            mid = await api.send_message(peer_id, T["admin_panel"], kb_admin())
            record_message(user_id, mid, "command")
            await _try_delete(api, peer_id, msg_id)
            return True

        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        await _try_delete(api, peer_id, msg_id)

        try:
            users = await get_all_user_ids(pool)
            ok = fail = 0
            for uid in users:
                try:
                    await api.send_message(uid, text)
                    ok += 1
                except Exception as e:
                    logger.warning(f"Не удалось отправить рассылку vk_id {uid}: {e}")
                    fail += 1
            txt = f"✅ Успех: {ok} | ❌ Ошибок: {fail}"
        except Exception as e:
            logger.error(f"Ошибка рассылки: {e}")
            txt = f"❌ {e}"

        mid = await api.send_message(peer_id, txt, kb_admin_back())
        record_message(user_id, mid, "command")
        return True

    if cur == S.ADMIN_DELETE_INPUT:
        if text.strip() in (T["cancel"], T["admin_back"]):
            await ctx.clear()
            await delete_all_bot_messages(user_id, api)
            mid = await api.send_message(peer_id, T["admin_panel"], kb_admin())
            record_message(user_id, mid, "command")
            await _try_delete(api, peer_id, msg_id)
            return True

        email = text.strip()
        try:
            is_valid, error_msg = validate_email(email, strict=True)
            if not is_valid:
                mid = await api.send_message(
                    peer_id,
                    T["admin_delete_error"].format(error=error_msg or "Некорректный e-mail"),
                    kb_admin_back(),
                )
                record_message(user_id, mid, "command")
                await _try_delete(api, peer_id, msg_id)
                return True

            username, owner_vk_id = await get_account_by_email(pool, email)
            if not username:
                mid = await api.send_message(
                    peer_id,
                    T["admin_delete_error"].format(error="Аккаунт не найден"),
                    kb_admin_back(),
                )
                record_message(user_id, mid, "command")
                await _try_delete(api, peer_id, msg_id)
                return True

            await ctx.update_data(email=email, username=username, owner_vk_id=owner_vk_id)
            await ctx.set_state(S.ADMIN_DELETE_CONFIRM)

            confirm_text = T["admin_delete_confirm"].format(email=email, username=username)
            confirm_kb = {
                "inline": True,
                "buttons": [[
                    {
                        "action": {"type": "callback", "label": T["admin_delete_confirm_yes"], "payload": '{"cmd":"admin_confirm_delete"}'},
                        "color": "negative",
                    },
                    {
                        "action": {"type": "callback", "label": T["admin_delete_confirm_no"], "payload": '{"cmd":"admin_back"}'},
                        "color": "primary",
                    },
                ]],
            }
            await _try_delete(api, peer_id, msg_id)
            mid = await api.send_message(peer_id, confirm_text, confirm_kb)
            record_message(user_id, mid, "command")
        except Exception as e:
            logger.error(f"Ошибка получения информации: {e}")
            await ctx.clear()
            mid = await api.send_message(peer_id, T["admin_delete_error"].format(error=str(e)), kb_admin_back())
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
