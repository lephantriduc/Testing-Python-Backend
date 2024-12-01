import random
import operations.base

from operations.add import Add
from operations.modulo import Modulo
from operations.exp import Exp

u = random.randint(1, 5)
v = random.randint(1, 3)

def mtfk():
    def another_one():
        raise NotImplementedError()

print(operations.base.__name__)

print(Add.eval(u, v))
print(Modulo.eval(u, v))
print(Exp.eval(u))