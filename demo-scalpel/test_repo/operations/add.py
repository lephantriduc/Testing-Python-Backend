from .base import Operator

class Add(Operator):
    @staticmethod
    def eval(u: int, v: int):
        return u + v
