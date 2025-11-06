from enum import StrEnum
from typing import Dict, List
from uuid import UUID
from faker import Faker
from faker.providers import DynamicProvider

G_FAKER = Faker()


class FieldEnum(StrEnum):
    ID = 'thr_id'
    TITLE = 'thr_title'
    DESCRIPTION = 'thr_description'
    EMAIL = 'thr_email'
    LOGIN = 'thr_login'
    FIRST_NAME = 'thr_first_name'
    LAST_NAME = 'thr_last_name'
    RATE = 'thr_rate'


class FieldFactory:

    @staticmethod
    def ID() -> UUID:
        return G_FAKER.uuid4()

    @staticmethod
    def TITLE() -> str:
        return G_FAKER.name()

    @staticmethod
    def DESCRIPTION(nb_words: int = 128) -> str:
        return G_FAKER.sentence(nb_words=nb_words)

    @staticmethod
    def EMAIL() -> str:
        return G_FAKER.email()

    @staticmethod
    def LOGIN() -> str:
        return G_FAKER.user_name()

    @staticmethod
    def FIRST_NAME() -> str:
        return G_FAKER.first_name()

    @staticmethod
    def LAST_NAME() -> str:
        return G_FAKER.last_name()

    @staticmethod
    def RATE(min: int = 0, max: int = 10):
        return G_FAKER.random_int(min=min, max=max)

    def __init__(
        self,
        field_list_dict: Dict[FieldEnum, List[str]] = {
            FieldEnum.TITLE: ['Titanic', 'Supermen', 'Fight club', 'Brave heart', 'Leon'],
            FieldEnum.EMAIL: ['peter.pen@xyz.com', 'hero@net.com', 'last_hero@nochance.net'],
            FieldEnum.DESCRIPTION: [
                'Titanic was a British ocean liner that sank in the early hours of 15 April 1912',
                'Superman is a superhero created by writer Jerry Siegel and artist Joe Shuster',
                'An insomniac office worker and a devil-may-care soap maker',
                'Tells the story of the legendary thirteenth century Scottish hero named William Wallace',
                'an Italian-American professional hitman who reluctantly takes in twelve-year-old Mathilda Lando',
            ],
            FieldEnum.LOGIN: ['admin', 'resool', 'leon', 'br_h', 'boat'],
            FieldEnum.FIRST_NAME: ['Peter', 'Vasya', 'Andrey', 'Ivan'],
            FieldEnum.LAST_NAME: ['Pupkin', 'Vasichkin', 'Ivanov', 'Sidorov'],
        },
    ):
        self._field_list_dict = field_list_dict
        self._faker = Faker()

        for k, v in field_list_dict.items():
            self._faker.add_provider(DynamicProvider(provider_name=k.value, elements=v))

    def title(self) -> str:
        return self._faker.thr_title()

    def description(self) -> str:
        return self._faker.thr_description()

    def email(self) -> str:
        return self._faker.thr_email()

    def login(self) -> str:
        return self._faker.thr_login()

    def first_name(self) -> str:
        return self._faker.thr_first_name()

    def last_name(self) -> str:
        return self._faker.thr_last_name()

    def get_dict_list(self, field_enum: FieldEnum) -> List[str]:
        return self._field_list_dict[field_enum]
