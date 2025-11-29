from typing import Callable
from injector import Module, Binder, singleton, provider

from models import Settings, DatabaseConfig
from interfaces import IAsyncSheetsService, IAsyncAPIService, IParser, IAsyncDatabaseService
from services import AsyncGoogleSheetsService, AsyncPokerHubAPIService
from services.database import AsyncPostgreSQLService
from parsers import CourseParser
from config import DatabaseConfigFactory


class AsyncApplicationModule(Module):


    def __init__(self, settings: Settings):
        self.settings = settings

    def configure(self, binder: Binder) -> None:
        binder.bind(Settings, to=self.settings, scope=singleton)

    @singleton
    @provider
    def provide_sheets_service(self, settings: Settings) -> IAsyncSheetsService:
        return AsyncGoogleSheetsService(settings.google_sheets_config)

    @singleton
    @provider
    def provide_api_service(self, settings: Settings) -> IAsyncAPIService:
        return AsyncPokerHubAPIService(settings.pokerhub_api_url)

    @singleton
    @provider
    def provide_parser(self) -> IParser:
        return CourseParser()

    @singleton
    @provider
    def provide_database_factory(self, settings: Settings) -> DatabaseConfigFactory:
        return DatabaseConfigFactory(settings)

    @singleton
    @provider
    def provide_database_service_factory(
        self
    ) -> Callable[[DatabaseConfig], IAsyncDatabaseService]:

        def factory(config: DatabaseConfig) -> IAsyncDatabaseService:
            return AsyncPostgreSQLService(config)

        return factory
