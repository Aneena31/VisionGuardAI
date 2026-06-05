from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.schemas.common import make_response
from db.database import get_db
from db.models import Notification


router = APIRouter(prefix="/visionguard/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(request: Request, db: Session = Depends(get_db)):
    items = db.query(Notification).order_by(Notification.created_at.desc()).limit(50).all()
    return make_response(
        {
            "unreadCount": sum(1 for item in items if not item.read),
            "items": [
                {
                    "id": item.id,
                    "type": item.type,
                    "title": item.title,
                    "message": item.message,
                    "createdAt": item.created_at.isoformat() + "Z" if item.created_at else None,
                    "read": bool(item.read),
                }
                for item in items
            ],
        },
        request.state.request_id,
    )


@router.post("/{notification_id}/read")
def mark_notification_read(notification_id: str, request: Request, db: Session = Depends(get_db)):
    notification = db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail=f"Notification {notification_id} was not found.")
    notification.read = True
    db.commit()
    return make_response(
        {
            "id": notification.id,
            "read": True,
        },
        request.state.request_id,
    )
