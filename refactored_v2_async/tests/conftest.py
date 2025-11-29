
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import List, Dict, Any

from models import (
    Settings,
    DatabaseConfig,
    SSHConfig,
    GoogleSheetsConfig,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    return Settings(
        spreadsheet_url="https://docs.google.com/spreadsheets/d/test123",
        service_account_file="test_service_account.json",
        db_user="test_user",
        db_password="test_password",
        db_host="127.0.0.1",
        db_port=5432,
        ssh_host="ssh.test.com",
        ssh_user="ssh_user",
        ssh_password="ssh_password",
        pokerhub_api_url="https://api.test.com/getusers",
        update_interval_minutes=60,
        timezone="Europe/Moscow",
        log_level="INFO"
    )


@pytest.fixture
def mock_db_config():
    return DatabaseConfig(
        name="test_db",
        host="127.0.0.1",
        port=5432,
        user="test_user",
        password="test_password",
        query="SELECT * FROM users",
        sheet_tab_name="TestSheet",
        start_row=1,
        column_range="A:R",
        clear_on_empty=False,
        ssh_config=None,
        use_pokerhub_data=False
    )


@pytest.fixture
def mock_db_config_with_pokerhub():
    ssh_config = SSHConfig(
        host="ssh.test.com",
        user="ssh_user",
        password="ssh_password",
        port=22,
        remote_db_port=5432
    )

    return DatabaseConfig(
        name="lead",
        host="localhost",
        port=5432,
        user="test_user",
        password="test_password",
        query="SELECT * FROM users",
        sheet_tab_name="pokerhub_robot",
        start_row=1,
        column_range="A:X",
        clear_on_empty=False,
        ssh_config=ssh_config,
        use_pokerhub_data=True
    )


@pytest.fixture
def mock_db_rows():
    return [
        ['id', 'username', 'first_name', 'last_name', 'date_registration',
         'user_block', 'source', 'campaign', 'content', 'medium', 'term', 'raw_link'],
        [1, 'user1', 'John', 'Doe', '2024-01-01', 'Нет',
         'source1', 'campaign1', 'content1', 'medium1', 'term1', 'link1'],
        [2, 'user2', 'Jane', 'Smith', '2024-01-02', 'Да',
         'source2', 'campaign2', 'content2', 'medium2', 'term2', 'link2'],
    ]


@pytest.fixture
def mock_pokerhub_response():
    return [
        {
            'tg_id': 1,
            'user_id': 1,
            'ph_nickname': 'player1',
            'ph_username': 'user1',
            'tg_username': 'tg_user1',
            'tg_nickname': 'TG User 1',
            'authorization_date': '2024-01-01T10:00:00Z',
            'last_visit_date': '2024-01-15T15:30:00Z',
            'referer': 'https://referer.com',
            'utm': {
                'utm_medium': 'social',
                'utm_source': 'facebook',
                'utm_campaign': 'winter2024'
            },
            'rc': 'ref123',
            'group': ['Group 1', 'MTT Course'],
            'courses': {
                'MTT Course 1': ['Модуль 1 Урок 1', 'Модуль 1 Урок 2']
            },
            'lessons': ['Модуль 2 Урок 1']
        },
        {
            'tg_id': 2,
            'user_id': 2,
            'courses': {
                'SPIN Course 1': ['Модуль 1 Урок 1']
            }
        }
    ]


@pytest.fixture
def mock_asyncpg_pool():
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()

    mock_conn.fetch = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_pool.acquire = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock()
    mock_pool.close = AsyncMock()

    return mock_pool


@pytest.fixture
def mock_gspread_async_client():
    mock_agc = AsyncMock()
    mock_spreadsheet = AsyncMock()
    mock_worksheet = AsyncMock()

    mock_worksheet.id = 123
    mock_worksheet.row_count = 1000
    mock_worksheet.update = AsyncMock()
    mock_worksheet.batch_clear = AsyncMock()

    mock_spreadsheet.worksheet = AsyncMock(return_value=mock_worksheet)
    mock_spreadsheet.batch_update = AsyncMock()

    mock_agc.open_by_url = AsyncMock(return_value=mock_spreadsheet)

    return mock_agc


@pytest.fixture
def mock_aiohttp_session():
    mock_session = AsyncMock()
    mock_response = AsyncMock()

    mock_response.json = AsyncMock(return_value=[])
    mock_response.raise_for_status = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock()

    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.close = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    return mock_session


@pytest.fixture
def mock_asyncpg_record():
    class MockRecord(dict):
        def keys(self):
            return super().keys()

        def values(self):
            return super().values()

    return MockRecord


@pytest.fixture
def sample_funnel_data():
    return {
        1: {
            'history': [
                {'label': 'action1', 'datetime': '2024-01-01'},
                {'label': 'action2', 'datetime': '2024-01-02'}
            ],
            'last_action_date': '2024-01-02',
            'state': 'active'
        },
        2: {
            'history': [],
            'last_action_date': '',
            'state': 'inactive'
        }
    }
