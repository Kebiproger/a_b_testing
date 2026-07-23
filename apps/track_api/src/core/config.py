from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Tracker API"
    RABBITMQ_URL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
