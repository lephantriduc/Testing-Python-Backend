import random


def input.another.print_hello():
    print('Hello!')


if random.random() < 0.5:
    input.another.print_hello()
from random import randint


def input.another.print_world():
    print('World!')


if randint(1, 100) <= 50:
    input.another.print_world()
    print_world()
