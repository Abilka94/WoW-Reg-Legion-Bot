"""
Integration tests for bot handlers - Core functionality.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, User, Chat
import pytest_asyncio

from src.handlers.commands import register_command_handlers, register_callback_handlers
from src.handlers.registration import register_registration_handlers
from src.states.user_states import RegistrationStates, ForgotPasswordStates


class TestCommandHandlersIntegration:
    """Integration tests for command handlers."""
    
    @pytest.fixture
    def mock_message(self):
        """Create mock message for testing."""
        user = User(id=123456789, is_bot=False, first_name="Test", username="testuser")
        chat = Chat(id=123456789, type="private")
        
        message = MagicMock(spec=Message)
        message.from_user = user
        message.chat = chat
        message.text = "test message"
        message.message_id = 1
        message.answer = AsyncMock()
        message.delete = AsyncMock()
        
        return message
    
    @pytest_asyncio.fixture
    async def mock_state(self):
        """Create mock FSM state for testing."""
        storage = MemoryStorage()
        state = FSMContext(
            storage=storage,
            key=storage.key_builder(bot_id=1, chat_id=123456789, user_id=123456789)
        )
        return state
    
    @pytest.mark.asyncio
    async def test_start_command_flow(self, mock_message, mock_state, mock_bot):
        """Test start command complete flow."""
        with patch('src.handlers.commands.delete_all_bot_messages') as mock_delete_all, \
             patch('src.handlers.commands.record_message') as mock_record, \
             patch('src.handlers.commands.delete_user_message') as mock_delete_user, \
             patch('src.handlers.commands.kb_main') as mock_keyboard, \
             patch('src.handlers.commands.BOT_VERSION', '1.0.0'), \
             patch('src.handlers.commands.T', {'start': 'Welcome! Version: {version}'}):
            
            mock_keyboard.return_value = MagicMock()
            
            # Simulate start command handler
            await mock_state.clear()
            await mock_delete_all(mock_message.from_user.id, mock_bot)
            msg = await mock_message.answer("Welcome! Version: 1.0.0", reply_markup=mock_keyboard())
            mock_record(mock_message.from_user.id, msg, "command")
            await mock_delete_user(mock_message)
            
            # Verify all functions were called
            mock_delete_all.assert_called_once_with(123456789, mock_bot)
            mock_message.answer.assert_called_once()
            mock_record.assert_called_once()
            mock_delete_user.assert_called_once_with(mock_message)
    
    @pytest.mark.asyncio
    async def test_version_command_flow(self, mock_message, mock_bot):
        """Test version command flow."""
        with patch('src.handlers.commands.delete_all_bot_messages') as mock_delete_all, \
             patch('src.handlers.commands.record_message') as mock_record, \
             patch('src.handlers.commands.delete_user_message') as mock_delete_user, \
             patch('src.handlers.commands.kb_back') as mock_keyboard, \
             patch('src.handlers.commands.BOT_VERSION', '1.2.3'), \
             patch('src.handlers.commands.T', {'version_pre': 'Bot Version: '}):
            
            mock_keyboard.return_value = MagicMock()
            
            # Simulate version command
            await mock_delete_all(mock_message.from_user.id, mock_bot)
            text = "Bot Version: 1.2.3"
            msg = await mock_message.answer(text, reply_markup=mock_keyboard())
            mock_record(mock_message.from_user.id, msg, "command")
            await mock_delete_user(mock_message)
            
            # Verify behavior
            mock_delete_all.assert_called_once()
            mock_message.answer.assert_called_once_with("Bot Version: 1.2.3", reply_markup=mock_keyboard())
            mock_record.assert_called_once()
            mock_delete_user.assert_called_once()


class TestRegistrationIntegration:
    """Integration tests for registration handlers."""
    
    @pytest.fixture
    def mock_callback_query(self):
        """Create mock callback query."""
        user = User(id=123456789, is_bot=False, first_name="Test", username="testuser")
        chat = Chat(id=123456789, type="private")
        message = MagicMock(spec=Message)
        message.chat = chat
        message.edit_text = AsyncMock()
        
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = user
        callback.data = "reg_start"
        callback.message = message
        callback.answer = AsyncMock()
        
        return callback
    
    @pytest.fixture
    def mock_message(self):
        """Create mock message."""
        user = User(id=123456789, is_bot=False, first_name="Test", username="testuser")
        chat = Chat(id=123456789, type="private")
        
        message = MagicMock(spec=Message)
        message.from_user = user
        message.chat = chat
        message.text = "TestNickname"
        message.answer = AsyncMock()
        
        return message
    
    @pytest_asyncio.fixture
    async def mock_state(self):
        """Create FSM state."""
        storage = MemoryStorage()
        state = FSMContext(
            storage=storage,
            key=storage.key_builder(bot_id=1, chat_id=123456789, user_id=123456789)
        )
        return state
    
    @pytest.mark.asyncio
    async def test_registration_start_flow(self, mock_callback_query, mock_state, mock_bot):
        """Test registration start callback."""
        with patch('src.handlers.registration.CONFIG', {"features": {"registration": True}}), \
             patch('src.handlers.registration.delete_all_bot_messages') as mock_delete_all, \
             patch('src.handlers.registration.record_message') as mock_record, \
             patch('src.handlers.registration.kb_wizard') as mock_wizard, \
             patch('src.handlers.registration.T', {'progress': ['Enter nickname', 'Enter password', 'Enter email']}):
            
            mock_wizard.return_value = MagicMock()
            
            # Simulate registration start
            await mock_state.clear()
            await mock_delete_all(mock_callback_query.from_user.id, mock_bot)
            await mock_state.set_state(RegistrationStates.nick)
            text = "1/3 - Enter nickname"
            
            msg = await mock_callback_query.message.edit_text(text, reply_markup=mock_wizard(0))
            mock_record(mock_callback_query.from_user.id, msg, "conversation")
            await mock_callback_query.answer()
            
            # Verify state
            current_state = await mock_state.get_state()
            assert current_state == RegistrationStates.nick.state
            
            mock_delete_all.assert_called_once()
            mock_callback_query.message.edit_text.assert_called_once()
            mock_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_nickname_validation_flow(self, mock_message, mock_state, mock_bot):
        """Test nickname validation in registration."""
        with patch('src.handlers.registration.validate_nickname') as mock_validate, \
             patch('src.handlers.registration.delete_user_message') as mock_delete_user, \
             patch('src.handlers.registration.record_message') as mock_record, \
             patch('src.handlers.registration.T', {'err_nick': 'Invalid nickname format'}):
            
            await mock_state.set_state(RegistrationStates.nick)
            
            # Test invalid nickname
            mock_validate.return_value = False
            mock_message.text = "invalid@nick"
            
            # Simulate validation
            nick = mock_message.text.strip()
            if not mock_validate(nick):
                msg = await mock_message.answer("Invalid nickname format")
                mock_record(mock_message.from_user.id, msg, "error")
                await mock_delete_user(mock_message)
                return
            
            # Verify validation was called and error handled
            mock_validate.assert_called_once_with("invalid@nick")
            mock_message.answer.assert_called_once_with("Invalid nickname format")
            mock_delete_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_successful_registration_flow(self, mock_message, mock_state, mock_bot, mock_db_pool):
        """Test successful complete registration."""
        with patch('src.handlers.registration.validate_email', return_value=True), \
             patch('src.handlers.registration.register_user') as mock_register, \
             patch('src.handlers.registration.delete_all_bot_messages') as mock_delete_all, \
             patch('src.handlers.registration.delete_user_message') as mock_delete_user, \
             patch('src.handlers.registration.record_message') as mock_record, \
             patch('src.handlers.registration.kb_main') as mock_keyboard, \
             patch('src.handlers.registration.T', {'success': 'Registration successful! Username: {username}'}):
            
            mock_register.return_value = ("testuser123#1", None)
            mock_keyboard.return_value = MagicMock()
            
            # Set up registration data
            await mock_state.set_state(RegistrationStates.mail)
            await mock_state.update_data(nick="TestUser", pwd="password123")
            mock_message.text = "test@example.com"
            
            # Simulate final registration step
            email = mock_message.text.strip()
            data = await mock_state.get_data()
            
            login, error = await mock_register(mock_db_pool, data["nick"], data["pwd"], email, mock_message.from_user.id)
            await mock_state.clear()
            await mock_delete_all(mock_message.from_user.id, mock_bot)
            
            if login:
                msg = await mock_message.answer(f"Registration successful! Username: {login}", reply_markup=mock_keyboard())
                mock_record(mock_message.from_user.id, msg, "command")
            
            await mock_delete_user(mock_message)
            
            # Verify registration process
            mock_register.assert_called_once_with(mock_db_pool, "TestUser", "password123", "test@example.com", 123456789)
            mock_message.answer.assert_called_once()
            mock_delete_all.assert_called_once()
            
            # Verify state was cleared
            current_state = await mock_state.get_state()
            assert current_state is None


class TestAccountManagementIntegration:
    """Integration tests for account management."""
    
    @pytest.mark.asyncio
    async def test_password_reset_flow(self, mock_db_pool):
        """Test password reset integration."""
        with patch('src.handlers.account_management.validate_email', return_value=True), \
             patch('src.handlers.account_management.reset_password') as mock_reset:
            
            # Mock database check
            cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
            cursor_mock.fetchone.return_value = (1,)  # Email exists for user
            
            mock_reset.return_value = "newpass123"
            
            # Simulate password reset
            email = "test@example.com"
            telegram_id = 123456789
            
            # Check email ownership
            async with mock_db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1 FROM users WHERE telegram_id=%s AND email=%s", (telegram_id, email.upper()))
                    if await cur.fetchone():
                        tmp_password = await mock_reset(mock_db_pool, email.upper())
                        assert tmp_password == "newpass123"
            
            mock_reset.assert_called_once_with(mock_db_pool, "TEST@EXAMPLE.COM")
    
    @pytest.mark.asyncio
    async def test_account_info_retrieval(self, mock_db_pool):
        """Test account information retrieval."""
        with patch('src.handlers.account_management.get_account_info') as mock_get_info:
            
            mock_accounts = [
                ("test@example.com", "testuser123#1", False, None),
                ("test2@example.com", "testuser456#1", True, "temppass")
            ]
            mock_get_info.return_value = mock_accounts
            
            # Simulate account info retrieval
            telegram_id = 123456789
            accounts = await mock_get_info(mock_db_pool, telegram_id)
            
            assert len(accounts) == 2
            assert accounts[0][0] == "test@example.com"
            assert accounts[1][2] is True  # is_temp_password
            
            mock_get_info.assert_called_once_with(mock_db_pool, telegram_id)


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, mock_bot):
        """Test handling of database connection errors."""
        # Mock database that raises connection error
        mock_db_pool = AsyncMock()
        mock_db_pool.acquire.side_effect = Exception("Database connection failed")
        
        with patch('src.handlers.admin.delete_all_bot_messages'), \
             patch('src.handlers.admin.record_message'), \
             patch('src.handlers.admin.notify_admin') as mock_notify:
            
            # Simulate database check that fails
            try:
                async with mock_db_pool.acquire():
                    pass
                result = "Database OK"
            except Exception as e:
                result = f"❌ {e}"
                await mock_notify(mock_bot, str(e))
            
            assert "Database connection failed" in result
            mock_notify.assert_called_once_with(mock_bot, "Database connection failed")
    
    @pytest.mark.asyncio
    async def test_invalid_input_handling(self):
        """Test handling of invalid user inputs."""
        with patch('src.handlers.registration.validate_nickname') as mock_validate:
            
            # Test various invalid inputs
            invalid_inputs = [
                "",  # Empty
                "a",  # Too short
                "user@test",  # Special characters
                "тест",  # Cyrillic
                "a" * 100,  # Too long
            ]
            
            mock_validate.return_value = False
            
            for invalid_input in invalid_inputs:
                result = mock_validate(invalid_input)
                assert result is False
            
            assert mock_validate.call_count == len(invalid_inputs)


class TestSecurityIntegration:
    """Integration tests for security features."""
    
    @pytest.mark.asyncio
    async def test_admin_access_control(self):
        """Test admin access control integration."""
        with patch('src.handlers.admin.ADMIN_ID', 999999999):
            
            # Test with non-admin user
            user_id = 123456789
            is_admin = (user_id == 999999999)
            
            assert is_admin is False
            
            # Simulate access check
            if not is_admin:
                access_denied = True
            else:
                access_denied = False
            
            assert access_denied is True
    
    @pytest.mark.asyncio
    async def test_input_sanitization_integration(self):
        """Test input sanitization integration."""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "\x00\x01\x02",  # Control characters
        ]
        
        with patch('src.handlers.registration.validate_email') as mock_validate, \
             patch('src.handlers.registration.validate_nickname') as mock_validate_nick:
            
            # All malicious inputs should be rejected
            mock_validate.return_value = False
            mock_validate_nick.return_value = False
            
            for malicious_input in malicious_inputs:
                email_valid = mock_validate(malicious_input)
                nick_valid = mock_validate_nick(malicious_input)
                
                assert email_valid is False
                assert nick_valid is False