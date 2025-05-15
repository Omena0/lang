
def std_print(*args):
    print(*args)

def std_output(*args):
    print(*args, end='')

def std_input(prompt):
    # Ensure we always get a string back from input
    result = input(prompt[0].strip('"').strip("'")) if len(prompt) else input()
    print(f"Debug: Input received: '{result}'")  # Add debug output to confirm input is received
    return result
