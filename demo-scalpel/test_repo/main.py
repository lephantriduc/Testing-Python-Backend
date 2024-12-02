import random
import operations.base

from test_repo.operations.add import Add
from test_repo.operations.modulo import Modulo
from test_repo.operations.exp import Exp

u = random.randint(1, 5)
v = random.randint(1, 3)

def mtfk():
    def another_one():
        raise NotImplementedError()

print(test_repo.operations.base.__name__)

print(Add.eval(u, v))
print(Modulo.eval(u, v))
print(Exp.eval(u))