import shlex
import sys
import os


operators = '+-*/%^&|!<>='


def prepareSource(src: str):
    fixed = ''
    for line in src.splitlines():
        line = line.split('//')[0]
        if not line.strip(): continue
        fixed += line + '\n'

    return fixed.replace('(', ' ( ').replace(')', ' ) ').replace('  ', ' ')


def calc(left: str, oper: str, right: str, vars: dict):
    # sourcery skip: remove-unnecessary-cast
    left = str(left)
    right = str(right)

    if not oper:
        if not left:
            if right:
                return right
            else:
                raise ValueError('No expression provided')
        if not right:
            return left

    if not left.replace('.', '', 1).isnumeric() and left:
        if left not in vars:
            raise UnboundLocalError(f'Variable {left} is not defined')

        left = str(vars[left]).strip()
        if left.startswith('(') and left.endswith(')'):
            left = evalExpr(left, vars)

    if not right.replace('.', '', 1).isnumeric() and right:
        if right not in vars:
            raise UnboundLocalError(f'Variable {right} is not defined')

        right = str(vars[right]).strip()
        if right.startswith('(') and right.endswith(')'):
            right = evalExpr(right, vars)

    match oper:
        case '+':
            return float(left) + float(right) if right else left
        case '-':
            return float(left) - float(right) if right else left
        case '*':
            return float(left) * float(right) if right else left
        case '/':
            return float(left) / float(right) if right else left
        case '^':
            return float(left) ** float(right) if right else left
        case '&':
            return bool(left) and bool(right)
        case '|':
            return bool(left) or bool(right)
        case '!':
            return not bool(right)
        case '%':
            return float(left) % float(right)
        case '<':
            return float(left) < float(right)
        case '>':
            return float(left) > float(right)
        case '<=':
            return float(left) <= float(right)
        case '>=':
            return float(left) >= float(right)
        case '==':
            return left == right
        case _:
            return right


def evalExpr(expr: str, vars, calledFromSelf=False):
    # sourcery skip: low-code-quality
    left = ''
    right = ''
    oper = ''
    seenOperator = False
    jumpToNext = 0
    jumps = 1

    for i, chr in enumerate(expr):
        if jumpToNext:
            if chr == ')':
                jumpToNext -= 1
                seenOperator = False
            continue

        if chr in operators:
            oper += chr
            seenOperator = True

        elif chr == '(':
            if seenOperator:
                jump, right = evalExpr(expr[i+1:], vars, calledFromSelf=True)
            else:
                jump, left = evalExpr(expr[i+1:], vars, calledFromSelf=True)

            jumpToNext += jump
            jumps += 1

        elif chr == ')':
            if calledFromSelf:
                return jumps, calc(left, oper, right, vars)
            return calc(left, oper, right, vars)

        elif not chr.strip():
            continue

        else:
            if seenOperator:
                right = str(right)
                right += chr
            else:
                left = str(left)
                left += chr

    if not left.isnumeric() and left not in vars and left:
        raise SyntaxError(f'{left} is not a defined variable or number.')

    if not right.isnumeric() and right not in vars and right:
        raise SyntaxError(f'{right} is not a defined variable or number.')

    if calledFromSelf:
        return 0, calc(left, oper, right, vars)

    if oper or right:
        r = calc(left, oper, right, vars)

    else:
        r = calc(left, '+', 0, vars)

    try: r = int(r)
    except Exception: ...

    return r


func = {}
### PARSE-TIME ###
def parseScope(src: str, rDepth=0):  # sourcery skip: low-code-quality
    locals = {}
    skip = 0
    code = []

    index = 0
    for index, line in enumerate(src.splitlines()):
        if skip:
            skip -= 1
            continue

        if not line.strip():
            continue

        name, *args = shlex.split(line.replace(',', ' ').strip(), posix=False)

        if name == 'fn':
            fname = args[0]
            fargs = []
            i = 1
            while '{' not in args[i]:
                cleanedArg = args[i].replace('(', '').replace(')', '').strip().removesuffix(',').strip()

                if cleanedArg:
                    fargs.append(cleanedArg)

                i += 1

            count = ''.join(src.splitlines()[index+1:]).count('{')+1
            scopeSrc = ''.join('\n'.join(src.splitlines()[index+1:]).replace('}', '|}').split('|')[:count])

            skip, funcLocals = parseScope(scopeSrc, rDepth+1)
            skip += 1

            skip_ = 0
            cleanLines = []
            for line in scopeSrc.splitlines():
                if skip_:
                    skip_ -= 1
                    continue

                line = line.strip()
                if not line:
                    continue

                elif line.startswith('let'):
                    continue

                elif line.startswith('fn'):
                    skip_ += '\n'.join(scopeSrc.splitlines()[i:]).count('\n', 0, scopeSrc.find('}'))
                    continue

                f, *args = line.split()
                line = f, ' '.join(args).strip().strip('()').strip()
                cleanLines.append(line)

            func[fname] = fargs, cleanLines, funcLocals

        elif name == 'let':
            value = line.split('=', 1)[1].strip().replace('true', '1').replace('false', '0')

            try:
                value = evalExpr(value, locals)
            except Exception:
                if debug: print('Could not eval')
                if not rDepth:
                    code.append((name, args))
                continue

            if debug: print(f'Setting {args[0]} to {value}')

            locals[args[0]] = value

        elif name == 'if':
            if '(' not in line or ')' not in line:
                line = line.replace(' ', '(', 1).replace(' ', ')', 1)
            if '(' not in line or ')' not in line:
                raise SyntaxError(f'Parse-time condition not found in {src.splitlines()[index]}.')

            cond = line.split('(')[1].split(')')[0].strip()
            cond = cond.replace('true', '1').replace('false', '0')
            try: cond = evalExpr(cond, locals)
            except Exception: ...
            else:
                found = 0
                skip = -3
                for line in src.splitlines()[index:]:
                    if '}' in line:
                        if not found: break
                        found -= 1
                    if '{' in line:
                        found += 1
                    if str(cond).replace('.0', '') == '0':
                        skip += 1
                    else:
                        cleanArgs = []
                        for arg in shlex.split(line, posix=False):
                            arg = arg.replace('(', '').replace(')', '').strip()
                            if arg:
                                cleanArgs.append(arg)
                        code.append(cleanArgs)

        elif not rDepth:
            cleanArgs = []
            for arg in args:
                arg = arg.replace('(', '').replace(')', '').strip()
                if arg:
                    cleanArgs.append(arg)

            code.append((name, cleanArgs))

    if not rDepth and 'main' not in src:
        func['main'] = ([], code, locals)

    return (index, locals) if rDepth else func


### RUN-TIME ###
def parseArgs(args, func, stdlib, vars):

    result = []
    for value in args:
        value = value.strip()

        try: v = evalExpr(value, vars)
        except Exception: ...
        else:
            result.append(v)
            continue

        if value.startswith('"') or value.replace('.', '', 1).isnumeric():
            v = value.strip('"')

        elif value in stdlib:
            v = stdlib[value](*args[1:])
            try: v.strip('"')
            except Exception: ...
            result.append(v)
            break

        elif value in func:
            v = runFunc(func, value, *args[1:])
            break

        elif value in '()':
            continue

        else:
            if not (value.replace('_', '').isalnum() and value[0].replace('_', 'a').isalpha()):
                raise SyntaxError(f'Unexpected "{value}" in runtime function call in {args}.')

            raise UnboundLocalError(f'Variable "{value}" is not defined in {args}.')

        try: v = int(v)
        except Exception:
            try: v = float(v)
            except Exception: ...

        result.append(v)

    return result


def runFunc(func, name, args):  # sourcery skip: low-code-quality
    if name not in func:
        raise NameError(f'Function {name} is not defined')

    if debug:
        print(f'Running function {name} with args {args}')

    argNames, code, vars = func[name]

    if len(argNames) != len(args):
        count = len(argNames)-len(args)
        print(args)
        if count > 0:
            raise TypeError(f'{name}() missing {count} argument{'s' if count > 1 else ''}: {', '.join(argNames[len(args):])}')
        else:
            raise TypeError(f'{name}() takes {len(argNames)} argument{'s' if len(argNames) > 1 else ''} but {len(args)} were given.')


    vars.update(dict(zip(argNames, args)))

    skip = 0
    for index, line in enumerate(code):
        if skip > 0:
            skip -= 1
            if debug: print(f'Skipping line {index}: {line}')
            continue

        fname = line[0]
        if fname == '}': continue

        if debug:
            print(f'Line: {line}')
            print(f'Fname: {fname}')

        if fname == 'ret':
            ret = (
                evalExpr(' '.join(line[1]), vars)
                if isinstance(line[1], list)
                else evalExpr(' '.join(line[1:]), vars)
            )
            if debug:
                print(f'Returning {ret}')
            return ret

        elif fname == 'let':
            # Runtime variable declaration
            varName, _, *varValue = line[1]
            try:
                varValue = evalExpr(' '.join(varValue), vars)
            except Exception:
                if debug:
                    print('Could not runtime eval')

            if varValue[0] in func:
                varValue = runFunc(func, varValue[0], varValue[2:-1])

            elif varValue[0] in stdlib:
                varValue = stdlib[varValue[0]](parseArgs(varValue[2:-1], func, stdlib, vars))

            vars[varName] = varValue

        elif fname == 'if':
            cond = line[1].removesuffix(') {').strip().replace('true', '1').replace('false', '0')
            cond = evalExpr(cond, vars)
            if str(cond).removesuffix('.0') == '0':
                found = 0
                for line in code[index+1:]:
                    if '}' in ''.join(line):
                        if not found:
                            break

                        found -= 1

                    elif '{' in ''.join(line):
                        found += 1

                    skip += 1

        elif fname == 'fn':
            for line in code[index-1:]:
                if line[0].endswith('}'):
                    break
                else:
                    skip += 1

        elif fname == 'import':
            if debug:
                print(f'Importing {line[1][0]}')
            with open(line[1][0]) as f:
                parseScope(prepareSource(f.read()))

        elif fname in stdlib:
            if debug:
                print(f'Using stdlib function {fname}')

            # Parse stdlib args
            funcArgs = parseArgs(line[1].split(','), func, stdlib, vars)
            stdlib[fname](*funcArgs)

        elif fname in func:
            # Parse func args
            funcArgs = parseArgs(line[1].split(','), func, stdlib, vars)
            runFunc(func, fname, funcArgs)

        elif (
            fname.replace('_', '').isalnum()
            and fname[0].replace('_', 'a').isalpha()
        ):
            raise NameError(f'Function "{fname}" is not defined.')
        else:
            raise UnboundLocalError(f'Unexpected "{fname}" in runtime function name.')


stdlib = {}
def load_stdlib(path: str = 'stdlib'):
    for file in os.listdir(path):
        if not file.endswith('.py'):
            continue
        if not os.path.isfile(os.path.join(path, file)):
            continue

        fname = file.split('.')[0]
        module = getattr(__import__(f'{path}.{fname}'), fname)

        for attr in dir(module):
            if not attr.startswith('std'):
                continue
            if not callable(getattr(module, attr)):
                continue
            stdlib[attr.removeprefix('std_')] = getattr(module, attr)


### RUN THE THING ###

load_stdlib()

src = prepareSource(open(sys.argv[1]).read())

debug = False

# Parse
parseScope(src)

if debug:
    print(func)

# Entry point
r = runFunc(func, 'main', [])

try:
    r = int(r)
except Exception:
    ...
sys.exit(r)
