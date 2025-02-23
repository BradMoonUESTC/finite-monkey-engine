from typing import Tuple, Type
from griffe import DocstringStyle
from pydantic_settings import BaseSettings, CliPositionalArg, PydanticBaseSettingsSource, PyprojectTomlConfigSettingsSource, SettingsConfigDict
from typing import Tuple, Type
from os import environ
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
)
class Settings(BaseSettings):
    model_config:SettingsConfigDict = SettingsConfigDict(
        cli_parse_args=True, 
        cli_prog_name='finite-monkey-engine',
        pyproject_toml_depth=0,
        pyproject_toml_table_header=('tool', 'finite-monkey-engine'),
        toml_file='pyproject.toml',
        extra='ignore',
        env_file ='.env',
        strict=False
    )
    #database_dsn:PostgresDsn = None
    id:str=""
    base_dir:str=""
    src_dir:str=""
    output:str="."
    AZURE_OR_OPENAI:str=""
    AZURE_API_BASE:str=""
    AZURE_API_KEY:str=""
    AZURE_API_VERSION:str=""
    AZURE_DEPLOYMENT_NAME:str=""
    BUSINESS_FLOW_COUNT:str="10"
    CLAUDE_MODEL:str=""
    COMMON_PROJECT:str=""
    COMMON_VUL:str="all"
    CONFIRMATION_MODEL:str=""
    DATABASE_SQLITE:str=""
    DATABASE_SETTINGS_URL:str=""
    DATABASE_URL:str="postgresql://postgres:1234@127.0.0.1:5432/postgres"
    ASYNC_DB_URL:str="postgresql+asyncpg://postgres:1234@127.0.0.1:5432/postgres"
    IGNORE_FOLDERS:str="test"
    MAX_THREADS_OF_CONFIRMATION:str="8"
    MAX_THREADS_OF_SCAN:str="8"
    OPENAI_API_BASE:str=""
    OPENAI_API_KEY:str=""
    OPENAI_MODEL:str=""
    OPTIMIZE:str=""
    PRE_TRAIN_MODEL:str=""
    SCAN_MODE:str="all"
    SPECIFIC_PROJECT:str=""
    SWITCH_BUSINESS_CODE:str="True"
    SWITCH_FUNCTION_CODE:str="False"
    GEMINI_API_KEY:str="k"
    PYTHONASYNCIODEBUG:str="1"
    FORCE_COLOR:str="1"
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        env_settings: PydanticBaseSettingsSource,
        init_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
       
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            PyprojectTomlConfigSettingsSource(settings_cls),
        )
    
class nodes_config(Settings):
    def nodes_config(self):
        model_config:SettingsConfigDict = SettingsConfigDict(
        cli_parse_args=True, 
        cli_prog_name='finite-monkey-engine',
        pyproject_toml_depth=0,
        pyproject_toml_table_header=('tool', 'finite-monkey-engine'),
        toml_file='pyproject.toml',
        extra='ignore',
        env_file ='.env',
        env_ignore_empty=True,
        strict=False,
        )
        self.settings = Settings()
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[Settings],
        env_settings: PydanticBaseSettingsSource,
        init_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
       
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            PyprojectTomlConfigSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
        )
    
