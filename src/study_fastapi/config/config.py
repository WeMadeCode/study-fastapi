from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url = ""
    redis_url = ""
    debug = False

    @field_validator("database_url")
    @classmethod
    def url_must_not_be_empty(cls, v: str):
        if not v:
            raise ValueError(
                "DATABASE_URL 没有配置 - 检查环境变量或者项目根目录的 .env 文件"
            )
        return v


settings = Settings()
