from fastapi import APIRouter

from app.api import auth, health, interviews, speech

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(interviews.router)
api_router.include_router(speech.router)
