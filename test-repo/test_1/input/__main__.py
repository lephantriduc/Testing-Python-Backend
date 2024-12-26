import random

if random.random() < 0.5:
    from input.another import print_hello
    print_hello()

from random import randint

if randint(1, 100) <= 50:
    from input.another import print_world
    print_world()