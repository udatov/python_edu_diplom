from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Recipients:
    all_users: bool
    user_ids: Optional[List[str]] = None


@dataclass
class PushNotify:
    recipients: Recipients
    title: str
    body: str
    image_url: Optional[str] = None
    action_url: Optional[str] = None
    ttl: Optional[int] = None
    event_type: Optional[str] = None
    entity_id: Optional[str] = None
    subject: Optional[str] = None
    text: Optional[str] = None
    send_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
