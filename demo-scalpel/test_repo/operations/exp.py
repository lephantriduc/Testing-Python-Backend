import math
from .base import Operator

class Exp(Operator):
    @staticmethod
    def eval(u: int):
        return math.exp(u)
