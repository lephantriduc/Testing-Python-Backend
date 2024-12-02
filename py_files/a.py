def do_something(x):
    if x % 2 == 0:
        x /= 2
    else:
        x = x * 3 + 1
    return x

def do_something_else(x):
    if x % 3 == 0:
        x /= 3
    elif x % 3 == 1:
        x * 2 + 1
    else:
        x - 1
    return x
