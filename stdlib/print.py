
def std_print(line, runFunc, func, vars, *args, **kwargs):
    if (not (
        line[1][0].startswith('"')
        or line[1][0].startswith("'")
        ) and not line[1][0].replace('.','',1).isnumeric()
    ):
        if line[1][0] in vars:
            v = vars[line[1][0]]
        elif line[1][0] in func:
            v = runFunc(func, line[1][0], line[1][1:])
        else:
            raise UnboundLocalError(f'Variable {line[1][0]} is not defined.')

    else:
        if isinstance(line[1],str):
            v = line[1]
        else:
            v = ' '.join(line[1])
    try:
        v = int(v)
    except: ...
    print(str(v).strip('\'"'))


def std_debug(line, runFunc, func, vars, *args, **kwargs):
    print(f'--- Debug ---\nFunc: {func}\nVars: {vars}\n')

