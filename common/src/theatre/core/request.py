from functools import cached_property
from typing import Any, AnyStr, Dict, List
from uuid import uuid4

import aiohttp
from fastapi import Request
from fastapi.datastructures import URL, Headers, QueryParams
from pydantic import BaseModel, Field, computed_field, model_serializer
from common.src.theatre.core.events import UgcEvent
from common.src.theatre.core.auth import JWTBearer
from datetime import datetime, timezone
import re

from common.src.theatre.schemas.auth_schemas import HttpToken, UserSubject


class ThinHttpRequest(BaseModel):

    @classmethod
    def url_to_dict(cls, url: URL) -> Dict[AnyStr, AnyStr]:
        return {
            "scheme": url.scheme,
            "path": url.path,
            "port": url.port,
            "netloc": url.netloc,
            "hostname": url.hostname,
        }

    http_request: Request = Field(..., exclude=True)
    occurred_at: datetime = Field(default=datetime.now(timezone.utc))

    class Config:
        arbitrary_types_allowed = True

    @computed_field(return_type=Dict[AnyStr, Any])
    @cached_property
    def headers(self) -> Dict[AnyStr, Any]:
        headers: Headers = self.http_request.headers
        return {h_key: headers.get(key=h_key) for h_key in headers.keys()}

    @computed_field(return_type=Dict[AnyStr, Any])
    @cached_property
    def query_params(self) -> Dict[AnyStr, Any]:
        query_params: QueryParams = self.http_request.query_params
        return {q_key: query_params.get(key=q_key) for q_key in query_params.keys()}

    @computed_field(return_type=Dict[str, Any])
    @cached_property
    def path_params(self) -> Dict[str, Any]:
        return self.http_request.path_params

    @model_serializer
    def ser_model(self) -> dict[str, Any]:
        return {
            "base_url": ThinHttpRequest.url_to_dict(self.http_request.base_url),
            "url": ThinHttpRequest.url_to_dict(self.http_request.url),
            "method": self.http_request.method,
            "headers": self.headers,
            "query_params": self.query_params,
            "path_params": self.path_params,
        }


class EventRequestState(BaseModel):

    http_request_state: dict[str, Any]
    user_subject: UserSubject

    @classmethod
    async def async_user_subject(cls, http_request_state: dict[str, Any]) -> UserSubject:
        headers: dict[str, Any] = http_request_state['headers']
        if 'authorization' in headers:
            auth_http_header: List[str] = str(headers['authorization']).split(sep=' ')
            if len(auth_http_header) != 2:
                raise ValueError(f"Invalid authorization header: {headers['authorization']}")
            encoded_token: str = auth_http_header[1]
            payload: Dict[str, Any] = await JWTBearer.parse_token(encoded_token)
            if not payload:
                raise ValueError(f"Failed to parse auth token: {encoded_token}")
            user_subject: UserSubject = UserSubject.model_validate_json(payload.get('sub'))
            return user_subject
        return None

    @computed_field
    @property
    def method(self) -> str:
        return self.http_request_state['method']

    @computed_field
    @property
    def url(self) -> str:
        return self.http_request_state['url']['path']

    @computed_field
    @property
    def authorize_evt(self) -> UgcEvent:
        is_authorization: bool = 'authorization' in self.http_request_state['headers']
        return UgcEvent.AUTHORIZATION_EVT if is_authorization else None

    @computed_field
    @property
    def login_evt(self) -> UgcEvent:
        url: str = self.http_request_state['url']['path']
        return UgcEvent.LOGIN_EVT if re.match('^.*/api/v1/login$', url) else None

    @computed_field
    @property
    def logout_evt(self) -> UgcEvent:
        url: str = self.http_request_state['url']['path']
        return UgcEvent.LOGOUT_EVT if re.match('^.*/api/v1/logout$', url) else None

    @computed_field
    @property
    def content_view_evt(self) -> UgcEvent:
        url: str = self.http_request_state['url']['path']
        content_prefix_url_re_list = [
            '^.*/api/v1/films(?:/).*$',
            '^.*/api/v1/persons(?:/).*$',
            '^.*/api/v1/genres(?:/).*$',
        ]
        return (
            UgcEvent.CONTENT_VIEW_EVT if any([re.match(url_re, url) for url_re in content_prefix_url_re_list]) else None
        )

    @computed_field
    @property
    def video_quality_adjust_evt(self) -> UgcEvent:
        url: str = self.http_request_state['url']['path']
        url_regex = '^.*/api/v1/watch(?:/).*$'
        query_params: dict[str, Any] = self.http_request_state['query_params']
        is_quality_query_param = 'quality' in query_params

        return UgcEvent.VIDEO_QUALITY_ADJUST_EVT if re.match(url_regex, url) and is_quality_query_param else None

    @computed_field
    def watch_movie_to_the_end_evt(self) -> UgcEvent:
        url: str = self.http_request_state['url']['path']
        url_regex = '^.*/api/v1/watch(?:/).*$'
        query_params: dict[str, Any] = self.http_request_state['query_params']
        is_watched_query_param = 'left' in query_params and query_params['left'] == 0
        return UgcEvent.VIDEO_QUALITY_ADJUST_EVT if re.match(url_regex, url) and is_watched_query_param else None

    @computed_field
    def search_filter_usage_evt(self) -> UgcEvent:
        url: str = self.http_request_state['url']['path']
        content_prefix_url_re_list = ['^.*/api/v1/films/search(?:/).*$', '^.*/api/v1/persons/search(?:/).*$']
        return (
            UgcEvent.CONTENT_VIEW_EVT if any([re.match(url_re, url) for url_re in content_prefix_url_re_list]) else None
        )

    @computed_field
    @property
    def event_list(self) -> List[UgcEvent]:
        return list(
            filter(
                lambda s: s,
                [
                    self.login_evt,
                    self.authorize_evt,
                    self.logout_evt,
                    self.content_view_evt,
                    self.video_quality_adjust_evt,
                    self.watch_movie_to_the_end_evt,
                    self.search_filter_usage_evt,
                ],
            )
        )


async def client_session():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


async def make_get_request(url, http_token: HttpToken, query_params: Dict[str, Any] = None):
    async with client_session.get(
        url,
        params=query_params,
        headers={
            'content-type': 'application/x-www-form-urlencoded',
            'Authorization': f'{http_token.token_type} {http_token.access_token}',
            'X-Request-Id': f'X_REQUEST_ID_{uuid4().hex[:7]}',
        },
    ) as response:
        body = await response.json()
        headers = response.headers
        status = response.status
    return {'body': body, 'status': status, 'headers': headers}
