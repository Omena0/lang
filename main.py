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

    if not left.replace('.', '', 1).isnumeric() and left and not left.startswith('"'):
        if left not in vars:
            raise UnboundLocalError(f'Variable {left} is not defined')

        left = str(vars[left]).strip()
        if left.startswith('(') and left.endswith(')'):
            left = evalExpr(left, vars)

    if not right.replace('.', '', 1).isnumeric() and right and not right.startswith('"'):
        if right not in vars:
            raise UnboundLocalError(f'Variable {right} is not defined')

        right = str(vars[right]).strip()
        if right.startswith('(') and right.endswith(')'):
            right = evalExpr(right, vars)

    left, right = left.strip('"'), right.strip('"')

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
        case '!=':
            return left != right
        case '=!':
            return left != right
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

    if expr.startswith('"') and expr.endswith('"') and expr.count('"') == 2:
        raise ValueError('Expression cannot be a string.')

    for chr in ',':
        if chr in expr:
            raise ValueError(f'Expression cannot contain "{chr}".')

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

    if (not left.isnumeric() or left.startswith('"')) and left not in vars and left:
        raise SyntaxError(f'{left} is not a defined variable or number.')

    if (not right.isnumeric() or right.startswith('"')) and right not in vars and right:
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
def parseArgs(args, func, stdlib, vars):  # sourcery skip: low-code-quality

    result = []
    for value in args:
        value = value.strip()

        # Try to eval argument
        try: v = evalExpr(value, vars)
        except Exception: ...
        else:
            result.append(v)
            continue

        # Strip string ""
        if value.startswith('"') or value.replace('.', '', 1).isnumeric():
            v = value.strip('"')

        # Check if it's a variable
        elif value in vars:
            v = vars[value]

        # Check if it's a stdlib function
        elif value in stdlib:
            v = stdlib[value](*parseArgs(args[1:], func, stdlib, vars))
            try: v.strip('"')
            except Exception: ...
            result.append(v)
            break

        # Check if it's a function
        elif value in func:
            v = runFunc(func, value, parseArgs(args[1:], func, stdlib, vars))
            break

        # Remove single parenthesis from args
        elif value in '()':
            continue

        else:
            # Nothing else fit, raise exception
            if not (value.replace('_', '').isalnum() and value[0].replace('_', 'a').isalpha()):
                raise SyntaxError(f'Unexpected "{value}" in runtime function call in {args}.')

            raise UnboundLocalError(f'Variable "{value}" is not defined in args {args}.')

        # Try to convert to int or float
        try: v = int(v)
        except Exception:
            try: v = float(v)
            except Exception: ...

        result.append(v)

    if len(result) == 1 and isinstance(result[0], list):
        result = result[0]

    if debug:
        print(f'ParseArgs: {args} --> {result}')

    return result


def runFunc(func, name, args):  # sourcery skip: low-code-quality
    if name not in func:
        raise NameError(f'Function {name} is not defined')

    if debug:
        print(f'Running function {name} with args {args}')

    argNames, code, vars = func[name]

    # Invalid number of args
    if len(argNames) != len(args):
        count = len(argNames)-len(args)
        print(args)
        if count > 0:
            raise TypeError(f'{name}() missing {count} argument{'s' if count > 1 else ''}: {', '.join(argNames[len(args):])}')
        else:
            raise TypeError(f'{name}() takes {len(argNames)} argument{'s' if len(argNames) > 1 else ''} but {len(args)} were given.')

    # Add to local variables
    vars.update(dict(zip(argNames, args)))

    # Run the actual code
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

        # Runtime keywords
        if fname == 'return':
            ret = line[1:]
            try:
                ret = evalExpr(' '.join(ret), vars)
            except Exception:
                if debug: print('Could not runtime eval.')

            # Is func?
            if ret[0] in func:
                ret = runFunc(func, ret[0], ret[1:])

            # Is stdlib?
            elif ret[0] in stdlib:
                ret = stdlib[ret[0]](parseArgs(','.join(ret[1:]).split(','), func, stdlib, vars))

            if debug:
                print(f'Returning {ret}')

            return ret

        elif fname == 'let':
            # Runtime variable declaration
            varName, _, *varValue = shlex.split(line[1].replace(' ( ', ' ').replace(',', ', '), posix=False)

            # If has an operator, try eval
            if any(op in varValue for op in operators):
                try:
                    varValue = evalExpr(' '.join(varValue), vars)
                except Exception:
                    if debug:
                        print('Could not runtime eval')

            # Variable Value parsing
            vv = []
            for i in varValue:
                # Is func?
                if i in func:
                    vv.append(runFunc(func, varValue[0], varValue[1:]))

                # Is stdlib?
                elif i in stdlib:
                    vv = parseArgs(','.join(varValue[1:]).split(','), func, stdlib, vars)
                    if debug: print(f'Using stdlib function {i} with {vv}')
                    vv = stdlib[i](vv)
                    return

                # Is var?
                elif i in vars:
                    vv.append(vars[i])

                # Else const
                else:
                    vv.append(i)

            vars[varName] = vv

        elif fname == 'if':
            # Clean line and try eval
            cond = line[1].removesuffix(') {').strip().replace('true', '1').replace('false', '0')
            cond = evalExpr(cond, vars)

            # Is false?
            if str(cond).removesuffix('.0') == '0':
                # Count number of lines to skip,
                # For every "{" it must find another "}".
                # After the amount of { is less than }, break the loop
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
            # Count number of lines to skip,
            # For every "{" it must find another "}".
            # After the amount of { is less than }, break the loop
            found = 0
            for line in code[index+1:]:
                if '}' in ''.join(line):
                    if not found:
                        break

                    found -= 1

                elif '{' in ''.join(line):
                    found += 1

                skip += 1

        elif fname == 'import':
            if debug:
                print(f'Importing {line[1][0]}')

            # Read file and parse it
            # Imported files are not RAN,
            # but their functions are added to the namespace
            with open(line[1][0]) as f:
                parseScope(prepareSource(f.read()))

        elif fname == 'expose':
            exposed = line[1][0]
            if debug:
                print(f'Exposing {exposed}')

            if exposed in globals():
                vars[exposed] = globals()[exposed]
            elif exposed in locals():
                vars[exposed] = globals()[exposed]
            elif exposed in dir(__builtins__):
                vars[exposed] = getattr(__builtins__, exposed)
            else:
                raise NameError(f'{exposed} is not defined.')

        elif fname in vars:
            if callable(vars[fname]):
                vars[fname](*parseArgs(line[1], func, stdlib, vars))

        elif fname in stdlib:
            # Parse stdlib args
            line_1 = line[1]
            if isinstance(line_1, list):
                line_1 = ','.join(line_1)
            funcArgs = parseArgs(line_1.split(','), func, stdlib, vars)

            if debug:
                print(f'Using stdlib function {fname} with {funcArgs}')

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
            stdlib[attr.removeprefix('std_')] = getattr(module, attr)


### RUN THE THING ###

load_stdlib()

src = prepareSource(open(sys.argv[1]).read())

debug = True

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
