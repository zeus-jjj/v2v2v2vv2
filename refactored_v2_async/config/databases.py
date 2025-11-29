import os
import logging
from pathlib import Path
from typing import List
import yaml

from models import DatabaseConfig, Settings

logger = logging.getLogger(__name__)


class DatabaseConfigFactory:
    STANDARD_QUERY = """
        SELECT id, username, first_name, last_name,
               DATE(timestamp_registration) AS date_registration,
               CASE WHEN user_block THEN 'Да' ELSE 'Нет' END AS user_block,
               source, campaign, content, medium, term, raw_link
        FROM users
        LEFT JOIN lead_resources ON users.id = lead_resources.user_id;
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    def create_bot_config(
        self,
        db_name: str,
        sheet_tab_name: str,
        column_range: str = "A:R",
        use_ssh: bool = False,
        use_pokerhub_data: bool = False
    ) -> DatabaseConfig:
        ssh_config = None
        if use_ssh:
            ssh_config = self.settings.get_ssh_config()
            if not ssh_config:
                raise ValueError(f"SSH config required for {db_name} but not provided")

        if use_pokerhub_data:
            column_range = "A:X"

        return DatabaseConfig(
            name=db_name,
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            query=self.STANDARD_QUERY,
            sheet_tab_name=sheet_tab_name,
            start_row=1,
            column_range=column_range,
            clear_on_empty=False,
            ssh_config=ssh_config,
            use_pokerhub_data=use_pokerhub_data
        )

    def create_all_configs(self) -> List[DatabaseConfig]:
        config_file = os.getenv('DB_CONFIG_FILE', 'config/databases.yaml')

        if Path(config_file).exists():
            logger.info(f"Loading database configs from YAML: {config_file}")
            return self._load_from_yaml(config_file)
        else:
            raise ValueError(
                f"Database configuration file not found: {config_file}\n"
                "Please create config/databases.yaml or set DB_CONFIG_FILE environment variable"
            )

    def _load_from_yaml(self, file_path: str) -> List[DatabaseConfig]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data or 'databases' not in data:
                raise ValueError("YAML must contain 'databases' key")

            configs = []
            for db_config in data['databases']:
                config = self.create_bot_config(
                    db_name=db_config['name'],
                    sheet_tab_name=db_config['sheet_tab'],
                    column_range=db_config.get('column_range', 'A:R'),
                    use_ssh=db_config.get('use_ssh', False),
                    use_pokerhub_data=db_config.get('use_pokerhub', False)
                )
                configs.append(config)

            logger.info(f"Loaded {len(configs)} database configs from YAML")
            return configs

        except Exception as e:
            logger.error(f"Failed to load YAML config: {e}")
            raise
