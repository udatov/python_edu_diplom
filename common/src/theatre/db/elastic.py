from typing import Any, Optional

import backoff
from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.exceptions import ApiError as ElasticSearchApiError
from elasticsearch.exceptions import TransportError as ElasticSearchTransportError

from common.src.theatre.db.base import DBType, UniversalReadDB


class ElasticDB(UniversalReadDB):
    def __init__(self, es: AsyncElasticsearch):
        self._es = es

    @backoff.on_exception(backoff.expo, (ElasticSearchApiError, ElasticSearchTransportError), max_tries=7)
    async def get_by_id(self, type_: DBType, id_: str) -> Optional[dict[str, Any]]:
        try:
            doc = await self._es.get(index=type_.value, id=id_)
        except NotFoundError:
            return None

        return doc['_source']

    async def get_by_id_list(self, type_: DBType, ids: list[str]) -> list[dict[str, Any]]:
        es_body = {
            'query': {'ids': {'values': ids}},
            'size': len(ids),
        }
        return await self._perform_search(index=type_.value, **es_body)

    async def search(
        self,
        type_: DBType,
        query: str,
        fields: list[str],
        page_number: int,
        page_size: int,
    ) -> list[dict[str, Any]]:
        es_body = {
            'query': {'multi_match': {'query': query, 'fields': fields}},
            'size': page_size,
            'from': (page_number - 1) * page_size,
        }
        return await self._perform_search(index=type_.value, **es_body)

    async def list_(
        self,
        type_: DBType,
        page_number: int,
        page_size: int,
        sort: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        es_body = {
            'size': page_size,
            'from': (page_number - 1) * page_size,
            'sort': self._sort_to_elastic(sort),
        }
        return await self._perform_search(index=type_.value, **es_body)

    async def list_films_by_genre(
        self,
        page_number: int,
        page_size: int,
        sort: Optional[str] = None,
        genre_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        query = None
        if genre_id:
            query = {
                'bool': {
                    'should': {
                        'nested': {
                            'path': 'genres',
                            'query': {'term': {'genres.id': {'value': genre_id}}},
                        }
                    }
                }
            }
        es_body = {
            'size': page_size,
            'from': (page_number - 1) * page_size,
            'query': query,
            'sort': self._sort_to_elastic(sort),
        }
        return await self._perform_search(index=DBType.MOVIE.value, **es_body)

    @backoff.on_exception(backoff.expo, (ElasticSearchApiError, ElasticSearchTransportError), max_tries=7)
    async def _perform_search(self, index: str, **kwargs) -> list[dict[str, Any]]:
        """Непосредственно производит поиск в ElasticSearch и очищает результаты."""
        doc = await self._es.search(index=index, **kwargs)
        return [hit['_source'] for hit in doc['hits']['hits']]

    def _sort_to_elastic(self, sort: Optional[str]) -> Optional[str]:
        """
        Преобразует строку сортировки в формат Elasticsearch.

        - sort: Строка сортировки.
        """
        if not sort:
            return None
        direction = 'desc' if sort.startswith('-') else 'asc'
        field = sort.split('-')[-1]
        if field in ['title', 'name', 'full_name']:
            field += '.raw'
        return f'{field}:{direction}'
