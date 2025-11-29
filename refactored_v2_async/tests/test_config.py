import pytest
from config import DatabaseConfigFactory
from models import Settings, DatabaseConfig


class TestDatabaseConfigFactory:
    def test_init(self, mock_settings):
        factory = DatabaseConfigFactory(mock_settings)
        assert factory.settings == mock_settings

    def test_standard_query(self, mock_settings):
        factory = DatabaseConfigFactory(mock_settings)
        assert "SELECT id, username" in factory.STANDARD_QUERY
        assert "FROM users" in factory.STANDARD_QUERY
        assert "LEFT JOIN lead_resources" in factory.STANDARD_QUERY

    def test_create_bot_config_standard(self, mock_settings):
        factory = DatabaseConfigFactory(mock_settings)
        config = factory.create_bot_config("test_db", "TestSheet")
        assert isinstance(config, DatabaseConfig)
        assert config.name == "test_db"
        assert config.sheet_tab_name == "TestSheet"
        assert config.column_range == "A:R"
        assert config.ssh_config is None
        assert config.use_pokerhub_data is False

    def test_create_bot_config_with_ssh(self, mock_settings):
        factory = DatabaseConfigFactory(mock_settings)
        config = factory.create_bot_config(
            "test_db",
            "TestSheet",
            use_ssh=True
        )
        assert config.ssh_config is not None
        assert config.ssh_config.host == mock_settings.ssh_host

    def test_create_bot_config_with_pokerhub(self, mock_settings):
        factory = DatabaseConfigFactory(mock_settings)
        config = factory.create_bot_config(
            "test_db",
            "TestSheet",
            use_pokerhub_data=True
        )
        assert config.use_pokerhub_data is True
        assert config.column_range == "A:X"

    def test_create_bot_config_ssh_without_settings(self):
        settings = Settings(
            spreadsheet_url="https://test.com",
            db_password="test",
            ssh_host=None,
            ssh_user=None,
            ssh_password=None
        )
        factory = DatabaseConfigFactory(settings)

        with pytest.raises(ValueError, match="SSH config required"):
            factory.create_bot_config(
                "test_db",
                "TestSheet",
                use_ssh=True
            )

    def test_create_bot_config_custom_column_range(self, mock_settings):
        factory = DatabaseConfigFactory(mock_settings)
        config = factory.create_bot_config(
            "test_db",
            "TestSheet",
            column_range="A:Z"
        )
        assert config.column_range == "A:Z"

    def test_create_all_configs(self, mock_settings):
        factory = DatabaseConfigFactory(mock_settings)
        configs = factory.create_all_configs()
        assert len(configs) == 11
        assert configs[0].name == "tgads_bot1"
        assert configs[0].sheet_tab_name == "MetaMoves_bot"
        assert configs[0].use_pokerhub_data is False
        assert configs[10].name == "lead"
        assert configs[10].sheet_tab_name == "pokerhub_robot"
        assert configs[10].use_pokerhub_data is True
        assert configs[10].ssh_config is not None

    def test_all_bot_names_unique(self, mock_settings):
        factory = DatabaseConfigFactory(mock_settings)
        configs = factory.create_all_configs()
        names = [c.name for c in configs]
        assert len(names) == len(set(names))

    def test_all_sheet_tabs_unique(self, mock_settings):
        factory = DatabaseConfigFactory(mock_settings)
        configs = factory.create_all_configs()
        tabs = [c.sheet_tab_name for c in configs]
        assert len(tabs) == len(set(tabs))
