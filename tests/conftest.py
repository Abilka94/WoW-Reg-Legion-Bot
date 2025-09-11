"""
Test configuration and fixtures for the WoW Registration Bot test suite.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import aiosqlite
from faker import Faker

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Disable logging during tests unless specifically testing logging
logging.disable(logging.CRITICAL)

fake = Faker()

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "settings": {
            "max_accounts_per_user": 3,
            "registration_enabled": True,
            "password_reset_enabled": True,
        },
        "features": {
            "registration": True,
            "account_management": True,
            "admin_panel": True,
            "currency_shop": True,
        },
        "database": {
            "host": "localhost",
            "port": 3306,
            "name": "test_db",
            "user": "test_user",
            "password": "test_pass",
        }
    }

@pytest.fixture
async def mock_db_pool():
    """Mock database connection pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    cursor = AsyncMock()
    
    # Setup mock chain
    pool.acquire.return_value.__aenter__.return_value = conn
    conn.cursor.return_value.__aenter__.return_value = cursor
    
    # Default cursor behavior
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    cursor.rowcount = 1
    
    return pool

@pytest.fixture
async def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    db = await aiosqlite.connect(":memory:")
    
    # Create test tables similar to the real schema
    await db.execute("""
        CREATE TABLE battlenet_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(255) UNIQUE NOT NULL,
            sha_pass_hash VARCHAR(64) NOT NULL,
            is_temp_password BOOLEAN DEFAULT 0,
            temp_password VARCHAR(16) DEFAULT NULL
        )
    """)
    
    await db.execute("""
        CREATE TABLE account (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(32) UNIQUE NOT NULL,
            sha_pass_hash VARCHAR(40) NOT NULL,
            email VARCHAR(255) NOT NULL,
            battlenet_account INTEGER,
            coins INTEGER DEFAULT 0,
            FOREIGN KEY (battlenet_account) REFERENCES battlenet_accounts(id)
        )
    """)
    
    await db.execute("""
        CREATE TABLE account_access (
            id INTEGER NOT NULL,
            gmlevel INTEGER NOT NULL DEFAULT 0,
            RealmID INTEGER NOT NULL DEFAULT -1,
            PRIMARY KEY (id, RealmID),
            FOREIGN KEY (id) REFERENCES account(id) ON DELETE CASCADE
        )
    """)
    
    await db.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id BIGINT NOT NULL,
            email VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.commit()
    yield db
    await db.close()

@pytest.fixture
def valid_test_data():
    """Generate valid test data for testing."""
    return {
        "emails": [
            "user@example.com",
            "test.user@domain.org",
            "valid_email@test-domain.net",
            "user123@gmail.com",
            "firstname.lastname@company.co.uk",
        ],
        "nicknames": [
            "TestUser",
            "Player123",
            "GamerOne",
            "User2024",
            "TestAccount",
        ],
        "passwords": [
            "password123",
            "StrongPass1",
            "MySecretPwd",
            "GamePass2024",
            "ValidPassword",
        ],
        "telegram_ids": [
            123456789,
            987654321,
            555666777,
            111222333,
            999888777,
        ]
    }

@pytest.fixture
def invalid_test_data():
    """Generate invalid test data for testing."""
    return {
        "emails": [
            "invalid-email",
            "@domain.com",
            "user@",
            "user..name@domain.com",
            "user@domain",
            "",
            "a" * 300 + "@domain.com",  # Too long
            "user name@domain.com",  # Space
            "user@domain..com",  # Double dot
        ],
        "nicknames": [
            "",  # Empty
            "a",  # Too short
            "a" * 100,  # Too long
            "User@123",  # Special chars
            "Пользователь",  # Cyrillic
            "user name",  # Space
            "test-user",  # Hyphen
            "user.name",  # Dot
        ],
        "passwords": [
            "",  # Empty
            "пароль123",  # Cyrillic
            "Пароль",  # Cyrillic
            "тест",  # Cyrillic
            "пользователь",  # Cyrillic
        ]
    }

@pytest.fixture
def security_test_data():
    """Generate security test data for vulnerability testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1'; DELETE FROM account; --",
            "admin'--",
            "' UNION SELECT * FROM battlenet_accounts --",
        ],
        "xss_payloads": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
        ],
        "command_injection": [
            "; rm -rf /",
            "$(whoami)",
            "`ls -la`",
            "&& cat /etc/passwd",
        ],
        "long_strings": [
            "a" * 10000,  # Very long string
            "b" * 100000,  # Extremely long string
        ]
    }

@pytest.fixture
def mock_bot():
    """Mock Telegram bot for testing."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.get_me = AsyncMock()
    bot.get_me.return_value = MagicMock(
        id=123456789,
        username="test_bot",
        first_name="Test Bot",
        can_join_groups=True
    )
    return bot

@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    return redis

@pytest.fixture(autouse=True)
def reset_config():
    """Reset configuration after each test."""
    yield
    # Cleanup any global state if needed

class TestDataGenerator:
    """Helper class for generating test data."""
    
    @staticmethod
    def generate_email(valid=True):
        """Generate test email address."""
        if valid:
            return fake.email()
        else:
            return fake.word() + "@invalid"
    
    @staticmethod
    def generate_nickname(valid=True):
        """Generate test nickname."""
        if valid:
            return fake.user_name().replace(".", "").replace("_", "")[:20]
        else:
            return fake.word() + "@#$"
    
    @staticmethod
    def generate_password(valid=True):
        """Generate test password."""
        if valid:
            return fake.password(length=12, special_chars=False, digits=True, upper_case=True, lower_case=True)
        else:
            return "пароль123"  # Cyrillic password (invalid)
    
    @staticmethod
    def generate_telegram_id():
        """Generate test Telegram ID."""
        return fake.random_int(min=100000000, max=999999999)

@pytest.fixture
def test_data_generator():
    """Provide test data generator."""
    return TestDataGenerator()

# Performance testing fixtures
@pytest.fixture
def performance_config():
    """Configuration for performance tests."""
    return {
        "max_response_time": 1.0,  # seconds
        "concurrent_users": 100,
        "test_duration": 30,  # seconds
        "memory_limit": 100 * 1024 * 1024,  # 100MB
    }

# Test environment setup
def pytest_configure(config):
    """Configure pytest environment."""
    # Create reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Set test environment variables
    os.environ["TESTING"] = "1"
    os.environ["LOG_LEVEL"] = "ERROR"

def pytest_unconfigure(config):
    """Cleanup after tests."""
    # Cleanup test environment
    os.environ.pop("TESTING", None)
    os.environ.pop("LOG_LEVEL", None)