from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from common.src.theatre.models.base import Base
from common.src.theatre.db.base import DBType, UniversalReadDB

ModelType = TypeVar('ModelType', bound=Base)


class BaseService(Generic[ModelType], ABC):
    """Абстрактный базовый сервис, содержащий общие методы для работы с БД"""

    def __init__(self, db: UniversalReadDB):
        self.db = db

    @abstractmethod
    def _from_db(self, doc: dict) -> ModelType:
        """Абстрактный метод для преобразования dict в Pydantic-модель"""
        pass

    def _from_db_many(self, docs: List[dict]) -> List[ModelType]:
        """Применяет from_db ко всем документам в списке"""
        return [self._from_db(d) for d in docs if d]


class IdService(BaseService[ModelType]):
    """Сервис для получения объекта по ID"""

    async def base_get_by_id(self, db_type: DBType, obj_id: str) -> Optional[ModelType]:
        """Общий метод получения объекта по ID"""
        doc = await self.db.get_by_id(db_type, obj_id)
        return self._from_db(doc) if doc else None


class IdListService(BaseService[ModelType]):
    """Сервис для получения списка объектов по ID"""

    async def base_get_by_id_list(self, db_type: DBType, ids: List[str]) -> List[ModelType]:
        """Общий метод получения списка объектов по ID."""
        docs = await self.db.get_by_id_list(db_type, ids)
        return self._from_db_many(docs)


class SearchService(BaseService[ModelType]):
    """Сервис для поиска"""

    async def base_search(
        self,
        db_type: DBType,
        query: str,
        fields: List[str],
        page_number: int,
        page_size: int,
    ) -> List[ModelType]:
        """Базовый метод поиска"""
        docs = await self.db.search(db_type, query, fields, page_number, page_size)
        return self._from_db_many(docs)


class ListService(BaseService[ModelType]):
    """Сервис для получения списка объектов"""

    async def base_list_(
        self,
        db_type: DBType,
        page_number: int,
        page_size: int,
        sort: Optional[str] = None,
    ) -> List[ModelType]:
        """Базовый метод получения списка записей"""
        docs = await self.db.list_(db_type, page_number, page_size, sort)
        return self._from_db_many(docs)


class FilmFilterService(BaseService[ModelType]):
    """Сервис для фильтрации фильмов по жанру"""

    async def base_list_films_by_genre(
        self,
        page_number: int,
        page_size: int,
        sort: Optional[str] = None,
        genre_id: Optional[str] = None,
    ) -> List[ModelType]:
        """Базовый метод получения списка фильмов по жанру"""
        docs = await self.db.list_films_by_genre(page_number, page_size, sort, genre_id)
        return self._from_db_many(docs)


class PersonFilmsService(BaseService[ModelType]):
    """Сервис для получения фильмов по персоне"""

    @abstractmethod
    def _extract_film_ids_from_person(self, person_doc: dict) -> List[str]:
        """Абстрактный метод для извлечения id фильмов из документа персоны"""
        pass

    async def base_get_films_by_person_id(self, person_id: str) -> List[ModelType]:
        """Базовый метод получения списка фильмов для персоны"""
        person_doc = await self.db.get_by_id(DBType.PERSON, person_id)
        if not person_doc:
            return []

        film_ids = self._extract_film_ids_from_person(person_doc)
        if not film_ids:
            return []

        docs = await self.db.get_by_id_list(DBType.MOVIE, film_ids)
        return self._from_db_many(docs)
