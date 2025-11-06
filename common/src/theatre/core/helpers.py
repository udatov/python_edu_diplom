from logging import getLogger
from typing import Any, AnyStr, Callable, Dict, List, Type
from datetime import datetime  # noqa: F811
from dateutil.relativedelta import relativedelta
import importlib

logger = getLogger(__name__)


def unpack_dictionary(dict_obj: Dict[Any, Any]) -> List[Any]:
    return [kv[1] for kv in sorted(dict_obj.items())]


def get_exception_descsription(error: Exception) -> str:
    return f'ERROR: {error}\n' + f'Exception type: {type(error).__name__}\n' + f'Exception arguments: {error.args}'


def get_error_details(error: Exception, prefix_msg: str = '') -> str:
    return (
        f'ERROR: {prefix_msg} {error}\n'
        + f'Exception type: {type(error).__name__}\n'
        + f'Exception arguments: {error.args}'
    )


def logging_error(logger: Any, error: Exception, prefix_msg: AnyStr):
    logger.exception(get_error_details(error=error, prefix_msg=prefix_msg))


def execute_wrapped_method(func: Callable, args: List[Any], kwargs: Dict[Any, Any], self: Any = None):
    is_both_args_type = len(args) > 0 and len(kwargs) > 0
    is_args_only = len(args) > 0 and len(kwargs) == 0
    is_kwargs_only = len(args) == 0 and len(kwargs) > 0
    if is_both_args_type:
        return func(self, *args, **kwargs) if self else func(*args, **kwargs)
    elif is_args_only:
        return func(self, *args) if self else func(*args)
    elif is_kwargs_only:
        return func(self, **kwargs) if self else func(**kwargs)
    else:
        return func(self) if self else func()


async def execute_async_wrapped_method(func: Callable, args: List[Any], kwargs: Dict[Any, Any], self: Any = None):
    is_both_args_type = len(args) > 0 and len(kwargs) > 0
    is_args_only = len(args) > 0 and len(kwargs) == 0
    is_kwargs_only = len(args) == 0 and len(kwargs) > 0
    if is_both_args_type:
        return await func(self, *args, **kwargs) if self else await func(*args, **kwargs)
    elif is_args_only:
        return await func(self, *args) if self else await func(*args)
    elif is_kwargs_only:
        return await func(self, **kwargs) if self else await func(**kwargs)
    else:
        return func(self) if self else func()


def days_between(d1: datetime, d2: datetime):
    return abs((d2 - d1).days)


def seconds_between(d1: datetime, d2: datetime) -> int:
    return abs(days_between(d1=d1, d2=d2) * 24 * 60 * 60)


def get_year_month_list() -> List[datetime]:
    current_year: int = datetime.now().year
    start_date: datetime = datetime(year=current_year, month=1, day=1, hour=0, minute=0, second=0)
    end_date: datetime = datetime(year=current_year + 1, month=1, day=1, hour=0, minute=0, second=0)
    result: List[datetime] = []
    current_date = start_date
    while current_date < end_date:
        result.append(current_date)
        current_date += relativedelta(months=1)

    return result


def cls_to_str(cls: Type[Any]) -> str:
    """Конвертируем любой тип в строковое представление. Используется для сохранения типов в БД"""
    return f'{cls.__module__}.{cls.__class__.__name__}'


def str_to_cls(cls_path: str) -> Type[Any]:
    """Реконструируем любой тип из его строкового представления. Используется для сохранения типов в БД"""
    module_name, class_name = cls_path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def build_response_body(
    msg: str, level: str = 'info', status: int = 200, details: str = "", payload: Dict[str, Any] = None
) -> Dict[str, Any]:
    return {'msg': msg, 'level': level, 'status': status, 'details': details, 'payload': payload}


if __name__ == '__main__':
    for month_date in get_year_month_list():
        print(month_date.strftime('%Y-%m'))
