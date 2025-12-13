"""
Главный файл приложения.
Система автоматического распознавания жестов и движений.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from src.app.routers import health, capture, recognize, settings as settings_router, record
from src.app.config import settings
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Создание и настройка приложения FastAPI.
    
    Returns:
        Настроенное приложение FastAPI
    """
    app = FastAPI(
        title=settings.app_name,
        description="Система автоматического распознавания жестов и движений",
        version="1.0.0",
        debug=settings.debug
    )
    
    # CORS middleware для разработки
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Подключение статических файлов (веб-интерфейс)
    app.mount("/static", StaticFiles(directory="web", html=True), name="static")
    
    # Корневой редирект на веб-интерфейс
    @app.get("/")
    def root_redirect():
        return RedirectResponse(url='/static/')
    
    # Подключение роутеров
    app.include_router(health.router)
    app.include_router(capture.router)
    app.include_router(recognize.router)
    app.include_router(settings_router.router)
    app.include_router(record.router)
    
    logger.info(f"Приложение {settings.app_name} инициализировано")
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
