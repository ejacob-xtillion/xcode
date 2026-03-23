from fastapi import FastAPI
from app.core.health_routes import router as health_router
from app.api.agents.routes import router as agents_router
from app.api.tools.routes import router as tools_router


def register_routers(app: FastAPI) -> None:
    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(agents_router, prefix="/agents", tags=["agents"])
    app.include_router(tools_router, prefix="/tools", tags=["tools"])
