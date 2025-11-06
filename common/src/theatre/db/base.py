from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, TypeVar, Union

from pydantic import BaseModel

from common.src.theatre.models.base import UUIDMixin

es: Union['UniversalReadDB', 'DBFilmFilter'] = None

db: Optional['UniversalReadDB'] = None

login_history_item_db: Optional['UniversalReadDB'] = None


"""
Результат запроса
"""
R = TypeVar('R')


async def get_es() -> 'UniversalReadDB':
    return es


async def get_db() -> 'UniversalReadDB':
    return db


async def get_login_history_item_db() -> 'UniversalReadDB':
    return login_history_item_db


class DBType(Enum):
    USER = 'users'
    LOGINHISTORYITEM = 'loginhistoryitems'
    PERSON = 'persons'
    MOVIE = 'movies'
    GENRE = 'genres'
    NOTIFICATION = 'notification'
    PAYMENT = 'payment'


class DBId(ABC):
    """Абстрактный класс для базы данных, умеющий получать объекты по ID."""

    @abstractmethod
    async def get_by_id(self, type: DBType, id: str) -> Optional[dict[str, Any]]:
        """Возвращает объект из базы по его id.

        - type_: тип запрашиваемого объекта
        - id_: id запрашиваемого объекта
        """


class DBIdList(ABC):
    """Абстрактный класс для базы данных, умеющий получать список объектов по ID."""

    @abstractmethod
    async def get_by_id_list(self, type: DBType, ids: list[str]) -> list[dict[str, Any]]:
        """Возвращает список объектов из базы по их id.

        - type_: тип запрашиваемого объекта
        - ids: список id запрашиваемоых объектов
        """


class DBSearch(ABC):
    """Абстрактный класс для базы данных, умеющей искать объекты по данным в полях."""

    @abstractmethod
    async def search(
        self,
        type: DBType,
        query: str,
        fields: list[str],
        page_number: int,
        page_size: int,
    ) -> list[dict[str, Any]]:
        """Возвращает список объектов из базы соответствующих критериям поиска.

        - type_: тип запрашиваемого объекта
        - query: строка запроса
        - fields: список полей для поиска
        - page_number: номер страницы результатов
        - page_size: верхняя граница количества элементов в ответе
        """


class DBList(ABC):
    """Абстрактный класс для базы данных, умеющей выводить список объектов с сортировкой."""

    @abstractmethod
    async def list_(
        self,
        type: DBType,
        page_number: int,
        page_size: int,
        sort: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Возвращает список объектов из базы с сортировкой по полю.

        - type_: тип запрашиваемого объекта
        - page_number: номер страницы результатов
        - page_size: верхняя граница количества элементов в ответе
        - fields: список полей для поиска
        - sort: строка сортировки, содержит поле и опционально "-" в начале
        """


class DBFilmFilter(ABC):
    """Абстрактный класс для базы данных, умеющей выводить список фильмов с сортировкой по жанру."""

    @abstractmethod
    async def list_films_by_genre(
        self,
        page_number: int,
        page_size: int,
        sort: Optional[str] = None,
        genre_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Возвращает список фильмов из базы с фильтром по id жанра.

        - page_number: номер страницы результатов
        - page_size: верхняя граница количества элементов в ответе
        - sort: строка сортировки, содержит поле и опционально "-" в начале
        - genre_id: uuid жанра для фильтрации
        """


class DBAuth(ABC):
    @abstractmethod
    async def get_by_login(self, login: str, type: DBType = DBType.USER) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def check_password(self, login: str, password: str, type: DBType = DBType.USER) -> bool:
        pass


class DBIdCreate(ABC):
    @abstractmethod
    async def create(self, entity_dto: BaseModel) -> UUIDMixin:
        pass


class DBIdUpdate(ABC):
    @abstractmethod
    async def update(self, entity_dto: UUIDMixin) -> bool:
        pass


class DBIdDelete(ABC):
    @abstractmethod
    async def delete(self, entity_dto: UUIDMixin) -> bool:
        pass


class DBIdCRUD(DBIdCreate, DBId, DBIdUpdate, DBIdDelete):
    pass


class GenreDB(DBId, DBList):
    pass


class FilmDB(DBId, DBSearch, DBFilmFilter):
    pass


class PersonDB(DBId, DBIdList, DBSearch, DBList):
    pass


class UniversalReadDB(DBId, DBIdList, DBSearch, DBList):
    pass


class DqmLangStatementDB(ABC):
    """
    Базовый интерфейс к объект, который выполняет DQL и DML запросы
    """

    @abstractmethod
    async def select(self, query_body: str, **kwargs) -> R:
        pass

    @abstractmethod
    async def upsert(self, query_body: str, **kwargs) -> None:
        pass

    @abstractmethod
    async def delete(self, query_body: str, **kwargs) -> None:
        pass
