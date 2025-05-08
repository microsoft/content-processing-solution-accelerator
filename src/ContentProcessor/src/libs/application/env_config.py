from libs.base.application_models import ModelBaseSettings
from pydantic import Field


class EnvConfiguration(ModelBaseSettings):
    # APP_CONFIG_ENDPOINT
    app_config_endpoint: str = Field(default="https://example.com")
