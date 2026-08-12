from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ApplicationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "Project NIMO"
    default_currency: str = "GBP"
    default_locale: str = "en-GB"
    default_timezone: str = "Europe/London"


class PathSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_root: str = "data"
    prompts_root: str = "prompts"


class StorageSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    database_filename: str = "nimo.sqlite3"


class PrivacySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm_enabled_by_default: bool = False
    include_raw_descriptions_in_llm_payload: bool = False
    log_transaction_values: bool = False


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    application: ApplicationSettings = Field(default_factory=ApplicationSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)


class ThemeSurface(BaseModel):
    model_config = ConfigDict(extra="forbid")

    background: str
    primary: str
    secondary: str


class ThemeText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str
    secondary: str


class ThemeBrand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str
    secondary: str
    accent: str


class ThemeStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    positive: str
    warning: str
    negative: str


class ThemeCharts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categorical: list[str]


class ThemeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    name: str
    surface: ThemeSurface
    text: ThemeText
    brand: ThemeBrand
    border: str
    status: ThemeStatus
    charts: ThemeCharts
