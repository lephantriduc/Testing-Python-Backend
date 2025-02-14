from typing import ClassVar

from pydantic import BaseModel


class Model(BaseModel):
    b: int
    c: str

    @property
    def a(self):
        return '?'


x = Model(b=7, c="s")
print(x.a)