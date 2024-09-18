
def std_print(*args):
    print(*args)

def std_output(*args):
    print(*args, end='')

def std_input(prompt):
    return input(prompt[0].strip('"').strip("'")) if len(prompt) else input()


