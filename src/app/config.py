from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Gesture Recognition System"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
