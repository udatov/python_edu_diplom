# models/loginhistoryitem.py
from typing import List
import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from common.src.theatre.models.base import Base
from common.src.theatre.core.helpers import get_year_month_list
from sqlalchemy import UniqueConstraint, text
from sqlalchemy.ext.declarative import AbstractConcreteBase


def create_partition(target, connection, **kw) -> None:
    """
    Создаем партиции на каждый месяц текущего года + индексы
    """
    i = 0
    month_list: List[datetime.datetime] = get_year_month_list()

    while i + 1 < len(month_list):
        curr_date = month_list[i]
        next_date = month_list[i + 1]
        connection.execute(
            text(
                f"""CREATE TABLE IF NOT EXISTS "loginhistoryitems_{curr_date.strftime("%m%Y")}" PARTITION OF "loginhistoryitems" FOR VALUES FROM ('{curr_date.strftime("%Y-%m-%d")}') TO ('{next_date.strftime("%Y-%m-%d")}')"""
            )
        )
        connection.execute(
            text(
                f"""CREATE INDEX IF NOT EXISTS "loginhistoryitems_{curr_date.strftime("%m%Y")}_idx" ON loginhistoryitems_{curr_date.strftime("%m%Y")}(login_datetime)"""
            )
        )
        i += 1


def drop_partition(target, connection, **kw) -> None:
    """
    Создаем партиции на каждый месяц текущего года + индексы
    """
    i = 0
    month_list: List[datetime.datetime] = get_year_month_list()

    while i + 1 < len(month_list):
        connection.execute(
            text(f"""DROP TABLE IF EXISTS "loginhistoryitems_{month_list[i].strftime("%m%Y")}" CASCADE""")
        )
        i += 1


class LoginHistoryItemBase(AbstractConcreteBase, Base):
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    login_datetime = Column(DateTime, default=datetime.datetime.now(), primary_key=True)
    ip_address = Column(String(32), unique=False, nullable=False)
    browser = Column(String(255), nullable=True)

    def __init__(self, user_id, ip_address: str, browser: str = None) -> None:
        self.ip_address = ip_address
        self.browser = browser
        self.user_id = user_id
        self.login_datetime = datetime.datetime.now()


class LoginHistoryItem(LoginHistoryItemBase):
    __tablename__ = 'loginhistoryitems'
    __table_args__ = (
        UniqueConstraint('user_id', 'login_datetime'),
        {
            'postgresql_partition_by': 'RANGE (login_datetime)',
            'listeners': [('after_create', create_partition)],
        },
    )

    def __init__(self, user_id: UUID, ip_address: str, browser: str = None) -> None:
        LoginHistoryItemBase.__init__(self, user_id=user_id, ip_address=ip_address, browser=browser)
