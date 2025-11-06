from enum import StrEnum, auto


class UgcEvent(StrEnum):
    AUTHORIZATION_EVT = auto()
    LOGIN_EVT = auto()
    LOGOUT_EVT = auto()
    CONTENT_VIEW_EVT = auto()
    VIDEO_QUALITY_ADJUST_EVT = auto()
    WATCH_MOVIE_TO_THE_END_EVT = auto()
    SEARCH_FILTER_USAGE_EVT = auto()


class NotificationEvent(StrEnum):
    NEW_FILM_RELEASE_NOTIFY_EVT = auto()
    USER_REGISTRATION_NOTIFY_EVT = auto()
    REVIEW_LIKE_NOTIFY_EVT = auto()
    VIEWER_COMMENT_LIKE_NOTIFY_EVT = auto()
    OTHER_NOTIFY_EVT = auto()
