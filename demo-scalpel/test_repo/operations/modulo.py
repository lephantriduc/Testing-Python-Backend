from .base import Operator

class Modulo(Operator):
    @staticmethod
    def eval(u: int, v: int):
        return u % v
