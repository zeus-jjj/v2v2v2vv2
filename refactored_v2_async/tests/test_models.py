import pytest
from pydantic import ValidationError

from models import (
    Settings,
    DatabaseConfig,
    SSHConfig,
    GoogleSheetsConfig,
    PokerHubUser,
    PokerHubCourse,
    UTMData,
)


class TestSSHConfig:

    def test_init_valid(self):
        config = SSHConfig(
            host="ssh.example.com",
            user="testuser",
            password="testpass",
            port=22,
            remote_db_port=5432
        )

        assert config.host == "ssh.example.com"
        assert config.user == "testuser"
        assert config.port == 22

    def test_default_ports(self):
        config = SSHConfig(
            host="ssh.example.com",
            user="testuser",
            password="testpass"
        )

        assert config.port == 22
        assert config.remote_db_port == 5432

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            SSHConfig(host="ssh.example.com")


class TestDatabaseConfig:

    def test_init_valid(self):
        config = DatabaseConfig(
            name="testdb",
            user="testuser",
            password="testpass",
            query="SELECT * FROM users",
            sheet_tab_name="TestSheet"
        )

        assert config.name == "testdb"
        assert config.host == "127.0.0.1"
        assert config.port == 5432

    def test_column_range_validation(self):
        config = DatabaseConfig(
            name="testdb",
            user="testuser",
            password="testpass",
            query="SELECT *",
            sheet_tab_name="Test",
            column_range="A:Z"
        )

        assert config.column_range == "A:Z"

    def test_invalid_column_range(self):
        with pytest.raises(ValidationError, match="must be in format"):
            DatabaseConfig(
                name="testdb",
                user="testuser",
                password="testpass",
                query="SELECT *",
                sheet_tab_name="Test",
                column_range="INVALID"
            )

    def test_with_ssh_config(self):
        ssh = SSHConfig(
            host="ssh.test.com",
            user="sshuser",
            password="sshpass"
        )

        config = DatabaseConfig(
            name="testdb",
            user="testuser",
            password="testpass",
            query="SELECT *",
            sheet_tab_name="Test",
            ssh_config=ssh
        )

        assert config.ssh_config is not None
        assert config.ssh_config.host == "ssh.test.com"

    def test_pokerhub_data_flag(self):
        config = DatabaseConfig(
            name="testdb",
            user="testuser",
            password="testpass",
            query="SELECT *",
            sheet_tab_name="Test",
            use_pokerhub_data=True
        )

        assert config.use_pokerhub_data is True


class TestGoogleSheetsConfig:

    def test_init_valid(self):
        config = GoogleSheetsConfig(
            spreadsheet_url="https://docs.google.com/spreadsheets/d/test123",
            service_account_file="test.json"
        )

        assert "test123" in config.spreadsheet_url
        assert config.service_account_file == "test.json"

    def test_missing_fields(self):
        with pytest.raises(ValidationError):
            GoogleSheetsConfig(spreadsheet_url="https://test.com")


class TestSettings:

    def test_init_minimal(self):
        settings = Settings(
            spreadsheet_url="https://docs.google.com/spreadsheets/d/test",
            db_password="testpass"
        )

        assert settings.db_user == "postgres"
        assert settings.db_host == "127.0.0.1"
        assert settings.update_interval_minutes == 60

    def test_google_sheets_config_property(self):
        settings = Settings(
            spreadsheet_url="https://test.com",
            db_password="pass"
        )

        config = settings.google_sheets_config
        assert isinstance(config, GoogleSheetsConfig)
        assert config.spreadsheet_url == "https://test.com"

    def test_get_ssh_config_none(self):
        settings = Settings(
            spreadsheet_url="https://test.com",
            db_password="pass",
            ssh_host=None,
            ssh_user=None,
            ssh_password=None
        )

        assert settings.get_ssh_config() is None

    def test_get_ssh_config_valid(self):
        settings = Settings(
            spreadsheet_url="https://test.com",
            db_password="pass",
            ssh_host="ssh.test.com",
            ssh_user="sshuser",
            ssh_password="sshpass"
        )

        ssh_config = settings.get_ssh_config()
        assert ssh_config is not None
        assert ssh_config.host == "ssh.test.com"


class TestUTMData:

    def test_init_valid(self):
        utm = UTMData(
            utm_medium="social",
            utm_source="facebook",
            utm_campaign="winter2024"
        )

        assert utm.utm_medium == "social"
        assert utm.utm_source == "facebook"

    def test_optional_fields(self):
        utm = UTMData()

        assert utm.utm_medium is None
        assert utm.utm_source is None


class TestPokerHubCourse:

    def test_init_valid(self):
        course = PokerHubCourse(
            name="MTT Course 1",
            lessons=["Lesson 1", "Lesson 2"]
        )

        assert course.name == "MTT Course 1"
        assert len(course.lessons) == 2

    def test_default_lessons(self):
        course = PokerHubCourse(name="Test Course")

        assert course.lessons == []


class TestPokerHubUser:

    def test_init_valid(self):
        user = PokerHubUser(
            user_id=1,
            tg_id=12345,
            ph_nickname="player1"
        )

        assert user.user_id == 1
        assert user.tg_id == 12345

    def test_with_utm_data(self):
        utm = UTMData(
            utm_medium="social",
            utm_source="facebook"
        )

        user = PokerHubUser(
            user_id=1,
            tg_id=12345,
            utm=utm
        )

        assert user.utm.utm_medium == "social"

    def test_default_collections(self):
        user = PokerHubUser(
            user_id=1,
            tg_id=12345
        )

        assert user.group == []
        assert user.courses == {}

    def test_alias_user_id(self):
        user = PokerHubUser(
            user_id=1,
            tg_id=12345
        )

        assert user.user_id == 1
