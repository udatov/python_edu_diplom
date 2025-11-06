from typing import Optional
from pydantic import UUID4, BaseModel, EmailStr, model_validator


class UserFilter(BaseModel):
    id: Optional[UUID4]
    ids: Optional[list[UUID4]]
    login: Optional[str]
    email: Optional[EmailStr]

    @model_validator(mode='after')
    def check_any_required_field(self):
        if not self.login and not self.email:
            raise ValueError('Either email or login are required')
        return self


class FilmFilter(BaseModel):
    id: Optional[UUID4]
    title: Optional[str]

    @model_validator(mode='after')
    def check_any_required_field(self):
        if not self.title or not self.id:
            raise ValueError('Either title or id are required')
        return self


class FilmRatingFilter(BaseModel):
    reviewer_id: Optional[UUID4]
    login: Optional[str]
    email: Optional[EmailStr]
    film_id: Optional[UUID4]
    film_title: Optional[str]

    @model_validator(mode='after')
    def check_any_required_field(self):
        no_reviewer_req_fields = not self.reviewer_id and (not self.login or not self.email)
        no_film_req_fields = not self.film_id and not self.film_title

        if no_reviewer_req_fields or no_film_req_fields:
            raise ValueError('Film and reviewer filter fields required')
        return self
