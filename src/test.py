from string import ascii_letters
from turtledemo.nim import randommove

from hypothesis import infer
from scalpel.typeinfer.typeinfer import TypeInference
import random

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


if __name__ == "__main__":
    inferer = TypeInference(
        name="type_infer_ex.py", entry_point="../uploads/my_project/type_infer_ex.py"
    )
    inferer.infer_types()
    inferred = inferer.get_types()

    randomized_inputs = {}
    for item in inferred:
        para_name = item.get('parameter', '')
        if para_name:
            type_name = item.get('type').pop()
            randomized_inputs[para_name] = randomize_type(type_name)
            print((para_name, type_name))

    print(randomized_inputs)
