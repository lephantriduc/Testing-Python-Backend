import random
from test_repo.operations.modulo import Modulo

def fun_a(a: int, b: int):
    if a == 0:
        return "A is the winner!"
    else:
        return fun_b(a, Modulo.eval(b, a))
    
def fun_b(a: int, b: int):
    if b == 0:
        return "B is the winner!"
    else:
        return fun_a(Modulo.eval(a, b), b)
    
for _ in range(10):
    a = random.randint(1, 10)
    b = random.randint(a, 10)