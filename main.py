import shlex
import sys
import os

operators = '+-*/^'


def prepareSource(src: str):
    fixed = ''
    for line in src.splitlines():
        line = line.split('//')[0]
        if not line.strip(): continue
        fixed += line + '\n'

    return fixed.replace('(', ' ( ').replace(')', ' ) ').replace('  ', ' ')


def calc(left: str, oper: str, right: str, vars: dict):
    left = str(left)
    right = str(right)

    if not oper:
        if not left:
            if not right:
                raise ValueError('No expression provided')
            return right
        if not right:
            if not left:
                raise ValueError('No expression provided')
            return left

    if not left.replace('.', '', 1).isnumeric():
        if left in vars:
            left = str(vars[left]).strip()
            if left.startswith('(') and left.endswith(')'):
                left = evalExpr(left, vars)
        else:
            raise UnboundLocalError(f'Variable {left} is not defined')

    if not right.replace('.', '', 1).isnumeric():
        if right in vars:
            right = str(vars[right]).strip()
            if right.startswith('(') and right.endswith(')'):
                right = evalExpr(right, vars)

        else:
            raise UnboundLocalError(f'Variable {right} is not defined')

    match oper:
        case '+':
            if right:
                return float(left) + float(right)
            return left

        case '-':
            if right:
                return float(left) - float(right)
            return left

        case '*':
            if right:
                return float(left) * float(right)
            return left

        case '/':
            if right:
                return float(left) / float(right)
            return left

        case '^':
            if right:
                return float(left) ** float(right)
            return left

        case _:
            return right


def evalExpr(expr: str, vars, r=False):
    left = ''
    right = ''
    oper = ''
    parseRight = False
    jumpToNext = 0
    jumps = 1

    for i, chr in enumerate(expr):
        if jumpToNext:
            if chr == ')':
                jumpToNext -= 1
                parseRight = False
            continue

        if chr in operators:
            if oper:
                raise SyntaxError(
                    f'Operator ({chr}) is already set (to {
                        oper}) at "{expr}" [{i}]'
                )

            oper = chr
            parseRight = True

        elif chr == '(':
            if parseRight:
                j, right = evalExpr(expr[i+1:], vars, r=True)
            else:
                j, left = evalExpr(expr[i+1:], vars, r=True)

            jumpToNext += j
            jumps += 1

        elif chr == ')':
            if r:
                return jumps, calc(left, oper, right, vars)
            return calc(left, oper, right, vars)

        elif not chr.strip():
            continue

        else:
            if parseRight:
                right = str(right)
                right += chr
            else:
                left = str(left)
                left += chr

    if r:
        return 0, calc(left, oper, right, vars)

    return calc(left, oper, right, vars)


func = {}

def parseScope(src: str, rDepth=0):
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

        name, *args = shlex.split(line.replace(',', ' ').strip())

        if name == 'fn':
            fname = args[0]
            fargs = []
            i = 1
            while '{' not in args[i]:
                a = args[i].replace('(', '').replace(
                    ')', '').strip().removesuffix(',').strip()

                if a:
                    fargs.append(a)
                i += 1

            c = ''.join(src.splitlines()[index+1:]).count('{')+1
            s = ''.join('\n'.join(src.splitlines()[index+1:]).replace('}','}|').split('|')[:c])

            skip, l = parseScope(s, rDepth+1)
            skip += 1

            skip_ = 0
            cleanLines = []
            for i_,line in enumerate(s.splitlines()):
                if skip_:
                    skip_ -= 1
                    continue
                line = line.strip()
                if not line:
                    continue

                if line.startswith('let'):
                    continue

                if line.startswith('fn'):
                    skip_ += '\n'.join(s.splitlines()[i:]).count('\n',0,s.find('}'))
                    continue

                f, *args = line.split()
                line = f, ' '.join(args).strip().strip('()').strip()
                cleanLines.append(line)

            func[fname] = fargs, cleanLines, l

        elif name == 'let':
            value = line.split('=', 1)[1].strip()

            try:
                value = evalExpr(value, locals)
            except UnboundLocalError:
                ...

            if debug: print(f'Setting {args[0]} to {value}')

            locals[args[0]] = value

        else:
            cleanArgs = []
            for arg in args:
                arg = arg.replace('(', '').replace(')', '').strip()
                if arg:
                    cleanArgs.append(arg)

            if not rDepth:
                code.append((name, cleanArgs))

    if not rDepth and 'main' not in src:
        func['main'] = ([], code, locals)

    if rDepth:
        return index, locals

    return func


def runFunc(func, name, args):
    if name not in func:
        raise NameError(f'Function {name} is not defined')

    if debug:
        print(f'Running function {name} with args {args}')

    argNames, code, vars = func[name]
    vars.update({k: v for k, v in zip(argNames, args)})

    skip = 0
    for index, line in enumerate(code):
        if skip > 0:
            skip -= 1
            print(f'Skipping line {index}: {line}')
            continue

        fname = line[0]
        if fname == '}': continue

        if debug:
            print(f'Line: {line}')
            print(f'Fname: {fname}')

        if fname == 'ret':
            if isinstance(line[1], list):
                ret = evalExpr(' '.join(line[1]), vars)
            else:
                ret = evalExpr(' '.join(line[1:]), vars)
            if debug:
                print(f'Returning {ret}')
            return ret

        elif fname == 'let':
            if debug:
                print('Why is let here?')

        elif fname == 'fn':
            if debug:
                print('Why is fn here?')
            for line in code[index-1:]:
                if line[-1].endswith('}'):
                    break
                skip += 1

        elif fname == 'import':
            if debug:
                print(f'Importing {line[1][0]}')
            with open(line[1][0]) as f:
                parseScope(prepareSource(f.read()))

        else:
            if fname in stdlib:
                if debug:
                    print(f'Using stdlib function {fname}')
                stdlib[fname](line, runFunc, func, vars)

            else:
                if fname in func:
                    runFunc(func, fname, args)

                else:
                    raise NameError(f'Function {fname} is not defined')


stdlib = {}


def load_stdlib(path: str = 'stdlib'):
    for file in os.listdir(path):
        if not file.endswith('.py'):
            continue
        if not os.path.isfile(os.path.join(path, file)):
            continue
        m = getattr(__import__(
            f'{path}.{file.split('.')[0]}'), file.split('.')[0])
        for attr in dir(m):
            if not attr.startswith('std'):
                continue
            if not callable(getattr(m, attr)):
                continue
            stdlib[attr.removeprefix('std_')] = getattr(m, attr)


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
except:
    ...
sys.exit(r)
