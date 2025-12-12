from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from src.app.routers import health, capture, recognize


def create_app() -> FastAPI:
    app = FastAPI(title="Gesture Recognition System")
    # mount static web UI at /static to avoid catching WebSocket scopes
    app.mount("/static", StaticFiles(directory="web", html=True), name="static")

    @app.get("/")
    def root_redirect():
        return RedirectResponse(url='/static/')

    app.include_router(health.router)
    app.include_router(capture.router)
    app.include_router(recognize.router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
