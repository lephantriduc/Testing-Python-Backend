from typing import TypeVar
from abc import ABC, abstractmethod

class Operator(ABC):
    @staticmethod  
    @abstractmethod  
    def eval(*args):
        pass