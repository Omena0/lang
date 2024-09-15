
def std_print(*args):
    print(*args)

def std_input(*args):
    return input(args[0].strip('"').strip("'")) if len(args) else input()


