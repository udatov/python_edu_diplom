from fastapi import APIRouter

from .notification import router as notification_router

router = APIRouter(
    prefix="/v1",
)

router.include_router(notification_router)
