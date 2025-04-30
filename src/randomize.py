import random
from string import ascii_letters

def randomize_type(type_kind):
    rand_bound = 10 ** 5
    str_len_bound = 100
    arr_len_bound = 10

    type_mapping = {
        'int': lambda: random.randint(-rand_bound, rand_bound),
        'str': lambda: ''.join(random.choices(ascii_letters, k=random.randint(1, str_len_bound))),
        'bool': lambda: random.choice([True, False]),
        'float': lambda: random.uniform(-rand_bound, rand_bound),
        'List[int]': lambda: [random.randint(-rand_bound, rand_bound) for _ in range(random.randint(0, arr_len_bound))]
    }

    if type_kind == 'any':
        type_kind = random.choice(list(type_mapping.keys()))

    return type_mapping[type_kind]()
