from functools import wraps
from logging import getLogger
from typing import Any, AnyStr, Callable, Dict, TypeVar
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from common.src.theatre.core.helpers import (
    logging_error,
    execute_wrapped_method,
    execute_async_wrapped_method,
    get_error_details,
)
from asyncio import iscoroutinefunction
from sqlalchemy.ext.asyncio import AsyncSession
from common.src.theatre.core.helpers import build_response_body

logger = getLogger(__name__)

E = TypeVar('E', bound=Exception)
R = TypeVar('R', bound=bool)


def get_auth_error(
    status_code: status = status.HTTP_401_UNAUTHORIZED,
    err_msg: str = 'Could not validate token',
    headers: Dict[AnyStr, AnyStr] = {'WWW-Authenticate': 'Bearer'},
) -> HTTPException:
    http_exception = HTTPException(
        status_code=status_code,
        detail=err_msg,
        headers=headers,
    )
    logging_error(logger=logger, error=http_exception, prefix_msg='[ Auth API ERROR ]: ')
    return http_exception


def process_error_result(
    err: Exception, wrap_error_type: type[E], is_raise_continue: bool = False, is_true_false_result: bool = False
):
    if is_raise_continue:
        raise wrap_error_type(err)
    return False if is_true_false_result else None


def default_error_handler(
    err: Exception,
    self_object: Any = None,
    wrapping_exception_context: Dict[AnyStr, AnyStr] = {},
    err_prefix_msg: str = 'Error happens',
    err_logger=logger,
    **kwargs,
):
    logging_error(logger=err_logger, error=err, prefix_msg=err_prefix_msg)
    raise err


async def sql_alchemy_error_handler(
    err: Exception,
    self_object: Any = None,
    wrapping_exception_type: type[E] = SQLAlchemyError,
    wrapping_exception_context: Dict[AnyStr, AnyStr] = {},
    err_prefix_msg: str = 'Error happens',
    err_logger=logger,
    **kwargs,
):
    logging_error(logger=err_logger, error=err, prefix_msg=err_prefix_msg)
    if self_object and hasattr(self_object, '_db_session') and self_object._db_session:
        logger.info(
            msg=f'sql_alchemy_error_handler: object has _db_session self_object={self_object}, try to rollback db session.'
        )
        db_session: AsyncSession = self_object._db_session
        try:
            await db_session.rollback()
        except Exception as err:
            logging_error(
                logger=err_logger, error=err, prefix_msg=f'{err_prefix_msg}, rollback session attemption failed: '
            )
    else:
        logger.info(msg=f'sql_alchemy_error_handler: object has NO _db_session self_object={self_object}')
    raise wrapping_exception_type(**wrapping_exception_context)


def fast_api_http_error_handler(
    err: Exception,
    wrapping_exception_type: type[E] = HTTPException,
    wrapping_exception_context: Dict[AnyStr, AnyStr] = {},
    err_prefix_msg: str = 'FastAPI Error: ',
    err_logger=logger,
    **kwargs,
) -> HTTPException:
    logging_error(logger=err_logger, error=err, prefix_msg=err_prefix_msg)
    wrapping_exception_context['detail'] = get_error_details(error=err)
    wrapping_exception_context['status_code'] = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(err, HTTPException):
        wrapping_exception_context['status_code'] = err.status_code
    raise wrapping_exception_type(**wrapping_exception_context)


def fast_api_http_error_response_handler(
    err: Exception,
    wrapping_exception_type: type[E] = HTTPException,
    wrapping_exception_context: Dict[AnyStr, AnyStr] = {},
    err_prefix_msg: str = 'FastAPI Error: ',
    err_logger=logger,
    **kwargs,
) -> HTTPException:
    logging_error(logger=err_logger, error=err, prefix_msg=err_prefix_msg)
    raise build_response_body(
        level='exception',
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=get_error_details(error=err),
        msg=f'{err_prefix_msg}{str(err)}',
    )


def filter_exception_decorator(
    err_logger=logger,
    filter_error_handler: Callable = default_error_handler,
    wrapping_exception_context: Dict[AnyStr, AnyStr] = {},
    err_prefix_msg: str = '',
):
    """
    Декоратор для обработки исключений: оборачивает пойманное исключение (`наслединк <Exception>`) в заданный тип исключения
    :param err_logger
    :param filter_error_handler Функция-обработчик оборачиваемого исключения
    :param wrapping_exception_context Задаем параметры инстанса исключение, в которое оборачиваем пойманную ошибку
    :param err_prefix_msg
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self=None, *args, **kwargs) -> R:
            try:
                if iscoroutinefunction(func):
                    return await execute_async_wrapped_method(func=func, self=self, args=args, kwargs=kwargs)
                else:
                    return execute_wrapped_method(func=func, self=self, args=args, kwargs=kwargs)

            except Exception as filter_err:
                return await filter_error_handler(
                    err=filter_err,
                    self_object=self,
                    wrapping_exception_context=wrapping_exception_context,
                    err_prefix_msg=err_prefix_msg,
                    err_logger=err_logger,
                    **kwargs,
                )

        return wrapper

    return decorator
