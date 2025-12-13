"""
Конфигурация приложения.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения."""
    app_name: str = "Gesture Recognition System"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    
    # Настройки захвата
    camera_device: int = 0
    enable_hands_detection: bool = True
    
    # Настройки предобработки
    smoothing_window: int = 5
    visibility_threshold: float = 0.5
    
    # Настройки распознавания
    recognition_history_size: int = 15
    
    # Путь к файлу маппингов
    mappings_file: str = "configs/mappings.yaml"
    
    # Путь к данным
    data_dir: str = "data"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
