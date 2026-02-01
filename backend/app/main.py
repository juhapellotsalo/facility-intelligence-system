import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import setup_logging
from app.routes.agent import router as agent_router
from app.routes.events import router as events_router
from app.routes.sensors import router as sensors_router

# Initialize logging before anything else
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Facility Intelligence System", version="0.1.0")
logger.info("FastAPI app created")

# Include routers
app.include_router(sensors_router)
app.include_router(events_router)
app.include_router(agent_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("Facility Intelligence System starting up")
    logger.info("API docs available at http://localhost:8000/docs")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
