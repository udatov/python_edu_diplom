import logging

from fastapi import Depends, BackgroundTasks, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import APIKeyHeader
from helpers.jwt_tockens import get_current_user_id
from models.mongo import Notification
from schemas.notification import (NotificationResponse, SendNotificationRequest, GetUserNotificationsResponse,
                                  GetUserNotificationsRequest, NotificationHistoryItem)
from services.notification import NotificationService, NotificationServiceException
from services.ws_connection_manager import get_connection_manager, WSConnectionManager
from starlette.status import HTTP_202_ACCEPTED, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_403_FORBIDDEN

from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/notifications",
)

api_key_header = APIKeyHeader(name="API-Key")


async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.notification_api_key:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key")
    return api_key


@router.post(
    "/send",
    response_model=NotificationResponse,
    status_code=HTTP_202_ACCEPTED,
    summary="Отправка сообщения",
    description="Отправка уведомления пользователям на основе события в системе.",
    dependencies=[Depends(get_api_key)],
)
async def send_notification(
        request: SendNotificationRequest,
        background_tasks: BackgroundTasks,
):
    try:
        response = await NotificationService.process_notification_request(
            request=request,
            background_tasks=background_tasks,
        )
        return response

    except NotificationServiceException as e:
        logger.exception(f"Error processing notification request: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Failed to process notification request: {str(e)}"
        )

    except Exception as e:
        logger.exception(f"Unexpected error in notification processing: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred. Please try again later."
        )


@router.post(
    "/history",
    response_model=GetUserNotificationsResponse,
    summary="Получение истории сообщений",
    description="Получение списка уведомлений, которые были отправлены пользователям.",
    dependencies=[Depends(get_api_key)],
)
async def get_user_notifications(request: GetUserNotificationsRequest):
    try:
        notifications = await Notification.get_notifications(
            user_ids=request.user_ids,
            notification_id=request.notification_id,
            channel=request.channel.value if request.channel else None,
            status=request.status.value if request.status else None,
            from_date=request.from_date,
            to_date=request.to_date,
            sort_by=request.sort_by,
            limit=request.limit,
            offset=request.offset,
        )

        total = await Notification.count_notifications(
            user_ids=request.user_ids,
            channel=request.channel.value if request.channel else None,
            status=request.status.value if request.status else None,
            from_date=request.from_date,
            to_date=request.to_date
        )

        notification_items = [
            NotificationHistoryItem(
                notification_id=notification.notification_id,
                user_id=notification.user_id,
                created_at=notification.created_at,
                sent_at=notification.sent_at,
                read_at=notification.read_at,
                channel=notification.channel,
                status=notification.status,
                error_message=notification.error_message,
            )
            for notification in await notifications.to_list()
        ]

        return GetUserNotificationsResponse(
            total=total,
            limit=request.limit,
            offset=request.offset,
            notifications=notification_items,
        )
    except Exception as e:
        logger.exception(f"Error retrieving user notifications: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve notifications history."
        )


@router.websocket("/ws")
async def websocket_endpoint(
        websocket: WebSocket,
        user_id: str = Depends(get_current_user_id),
        manager: WSConnectionManager = Depends(get_connection_manager),
):
    await websocket.accept()
    manager.connect(user_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
