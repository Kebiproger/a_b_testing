from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    RABBITMQ_URL: str
    CLICKHOUSE_HOST: str = "clickhouse"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""

    MAX_BATCH_SIZE: int = 5000
    MAX_TIMEOUT_SECONDS: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
