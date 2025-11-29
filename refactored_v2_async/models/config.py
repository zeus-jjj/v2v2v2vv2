from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SSHConfig(BaseModel):
    host: str = Field(..., description="SSH host")
    user: str = Field(..., description="SSH username")
    password: str = Field(..., description="SSH password")
    port: int = Field(22, description="SSH port")
    remote_db_port: int = Field(5432, description="Remote database port")


class DatabaseConfig(BaseModel):
    name: str = Field(..., description="Database name")
    host: str = Field("127.0.0.1", description="Database host")
    port: int = Field(5432, description="Database port")
    user: str = Field(..., description="Database user")
    password: str = Field(..., description="Database password")
    query: str = Field(..., description="SQL query to execute")

    sheet_tab_name: str = Field(..., description="Google Sheets tab name")
    start_row: int = Field(1, description="Starting row in sheet")
    column_range: str = Field("A:R", description="Column range")
    clear_on_empty: bool = Field(False, description="Clear sheet if empty")

    ssh_config: Optional[SSHConfig] = None
    use_pokerhub_data: bool = Field(False, description="Integrate PokerHub API data")

    @field_validator('column_range')
    @classmethod
    def validate_column_range(cls, v: str) -> str:
        if ':' not in v:
            raise ValueError("Column range must be in format 'A:Z'")
        return v


class GoogleSheetsConfig(BaseModel):
    spreadsheet_url: str = Field(..., description="Google Sheets URL")
    service_account_file: str = Field(..., description="Service account JSON file path")


class SchedulerConfig(BaseModel):
    update_interval_minutes: int = Field(60, description="Update interval in minutes")
    run_on_startup: bool = Field(True, description="Run update on startup")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )

    spreadsheet_url: str
    service_account_file: str

    db_user: str = "postgres"
    db_password: str
    db_host: str = "127.0.0.1"
    db_port: int = 5432

    ssh_host: Optional[str] = None
    ssh_user: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_port: int = 22
    remote_db_port: int = 5432

    pokerhub_api_url: str = "https://pokerhub.pro/api/tg/getusers"

    update_interval_minutes: int = 60

    timezone: str = "Europe/Moscow"

    log_level: str = "INFO"

    @property
    def google_sheets_config(self) -> GoogleSheetsConfig:
        return GoogleSheetsConfig(
            spreadsheet_url=self.spreadsheet_url,
            service_account_file=self.service_account_file
        )

    @property
    def scheduler_config(self) -> SchedulerConfig:
        return SchedulerConfig(
            update_interval_minutes=self.update_interval_minutes
        )

    def get_ssh_config(self) -> Optional[SSHConfig]:
        if not self.ssh_host:
            return None

        return SSHConfig(
            host=self.ssh_host,
            user=self.ssh_user,
            password=self.ssh_password,
            port=self.ssh_port,
            remote_db_port=self.remote_db_port
        )
