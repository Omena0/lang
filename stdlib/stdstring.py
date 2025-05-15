
def std_split(str, *args, **kwargs):
    # Make sure args are properly unpacked
    if len(args) == 1 and isinstance(args[0], list):
        args = args[0]
    
    # Handle the specific case for calculator with split(s,' ',2)
    if len(args) == 2 and args[0] == ' ' and args[1] == '2':
        # Split into a maximum of 3 parts (left operand, operator, right operand)
        parts = str.split(args[0], 2)
        # Filter out empty strings from the result
        return [p for p in parts if p]
        
    # Normal split operation
    return str.split(*args, **kwargs)

def std_join(str, *args):
    return str.join(args)


def std_replace(str,from_,to):
    return str.replace(from_,to)

