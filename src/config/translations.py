"""
Словарь переводов (RU)
"""

TRANSLATIONS = {
    # Общие
    "start": "Добро пожаловать!\n\nВерсия бота: {version}",
    "progress": ["Введите никнейм", "Введите пароль", "Введите e-mail"],
    "success": "Готово: аккаунт создан! Логин: <code>{username}</code>",
    "err_mail": "Некорректный e-mail.",
    "err_exists": "Такой e-mail уже зарегистрирован. Укажите другой.",
    "err_max_accounts": "Достигнут лимит аккаунтов: {max_accounts}.",
    "err_nick": "Некорректный никнейм. Используйте латиницу и цифры.",
    "err_pwd": "Некорректный пароль. Не используйте кириллицу.",
    "no_access": "Нет доступа.",
    "to_main": "На главную",
    "back": "◀️ Назад",
    "cancel": "Отмена",
    "version_pre": "Версия бота: ",
    "use_menu_or_start": "❓ Используйте меню или /start",

    # Меню
    "menu_reg": "Регистрация",
    "menu_info": "Как подключиться",
    "menu_news": "Новости",
    "menu_acc": "Мои аккаунты",
    "menu_fgt": "Сброс пароля",

    # Админка
    "admin_panel": "Админ-панель",
    "admin_db": "Проверить БД",
    "admin_bcast": "Рассылка",
    "admin_log": "Скачать лог",
    "admin_delete_account": "Удалить аккаунт",
    "admin_reload_config": "Перезагрузить конфиг",
    "admin_main": "На главную",
    "admin_back": "Назад в админку",
    "db_ok": "Соединение с БД: успешно.",
    "admin_broadcast_prompt": "🔹 Введите текст рассылки:",
    "admin_delete_prompt": "Введите e-mail аккаунта для удаления:",
    "admin_delete_success": "Аккаунт удалён: email={email}",
    "admin_delete_error": "Ошибка удаления аккаунта: {error}",
    "reload_config_success": "Конфигурация перезагружена.",
    "reload_config_error": "Ошибка перезагрузки конфигурации: {error}",
    "log_not_found": "❌ Лог файл не найден",

    # Аккаунты
    "account_info": "Ваш аккаунт:\nЛогин: <code>{username}</code>\nE-mail: <code>{email}</code>\nСтатус пароля: {password_status}",
    "account_no_account": "У вас нет привязанных аккаунтов.",
    "select_account_prompt": "Выберите аккаунт для просмотра:",
    "change_password_prompt": "Введите новый пароль:",
    "change_password_success": "Пароль успешно изменён!",
    "delete_account_prompt": "Удалить аккаунт",
    "delete_account_success": "Аккаунт удалён!",
    "delete_account_error": "Не удалось удалить аккаунт. Попробуйте позже.",
    "forgot_email_prompt": "🔄 Введите e-mail для сброса пароля:",
    "email_not_linked": "❌ E-mail не привязан к вашему Telegram.",
    "reset_success": "Пароль сброшен. Временный пароль: <code>{password}</code>\nПоменяйте его после входа.",
    "reset_err_not_found": "E-mail не найден.",
    "account_not_found_error": "Аккаунт не найден",

    # Магазин валюты
    "coins_menu": "🛒 <b>Магазин валюты</b>\n\nЗдесь вы можете купить монеты для аккаунта.",
    "buy_coins": "🛒 <b>Покупка валюты</b>\n\nВыберите пакет:",
    "btn_buy_coins": "💰 Купить валюту",
    "btn_check_balance": "💳 Мой баланс",
    "btn_pkg_100": "🪙 100 монет - 50₽",
    "btn_pkg_200": "🪙 200 монет - 90₽",
    "btn_pkg_300": "💰 300 монет - 130₽",
    "btn_pkg_400": "💰 400 монет - 160₽",
    "btn_pkg_500": "💎 500 монет - 200₽",
    "btn_pkg_custom": "✍️ Свое количество",
    "select_account_for_coins": "🛒 <b>Выбор аккаунта</b>\n\nДля какого e-mail пополнить баланс?",
    "enter_coins_amount": "🛒 <b>Своё количество</b>\n\nВведите число от 1 до 10000",
    "coins_purchased": "✅ <b>Покупка успешна!</b>\n\nНачислено: {amount} монет\n📧 Аккаунт: {email}\n💳 Баланс: {balance} монет",
    "coins_purchase_error": "❌ Ошибка при покупке. Повторите позже.",
    "invalid_coins_amount": "❌ Некорректное количество. Введите от 1 до 10000.",
    "account_balance": "💳 <b>Баланс аккаунтов</b>\n\n{accounts_info}",
    "no_accounts_for_coins": "Нет аккаунтов для операций с валютой.",
    "shop_disabled": "Магазин валюты отключен.",
    "purchase_disabled": "Покупки временно отключены.",
    "coins_entry": "📧 {email} (💰 {coins} монет)",

    # Инфраструктура
    "feature_disabled": "Функция отключена.",
    "database_unavailable": "Ошибка подключения к БД",
    "data_fetch_error": "Ошибка при получении данных",
    "custom_purchases_disabled": "Кастомные покупки отключены",
    "unknown_package": "Неизвестный пакет",
    "coins_amount_error": "Ошибка: не выбрано количество монет"
}
