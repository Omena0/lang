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
            v = value.strip('"')        # Check if it's a variable
        elif value in vars:
            v = vars[value]

        # Check if it's a stdlib function
        elif value in stdlib:
            parsed_args = parseArgs(args[1:], func, stdlib, vars)
            if debug: print(f'Calling stdlib function {value} with args: {parsed_args}')
            v = stdlib[value](*parsed_args)
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

    argNames, code, func_vars = func[name]

    # Create a new vars dict for this function call
    # Copy the vars to avoid modifying the original
    vars = func_vars.copy()

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
                        print('Could not runtime eval')            # Variable Value parsing
            vv = []                # Check if we're calling a stdlib function
            if len(varValue) > 0 and varValue[0] in stdlib:
                # For stdlib functions, parse arguments and call the function
                func_name = varValue[0]

                # Special handling for input function
                if func_name == "input":
                    # Special handling for input to ensure string value is stored correctly
                    prompt = ' '.join(varValue[1:]).strip('"')
                    result = input(prompt)
                    print(f"Debug: Direct input received: '{result}'")
                    vars[varName] = result
                    return

                # Special handling for index function used in calculator
                if func_name == "index":
                    # Get the variable name that should contain the list
                    list_var = varValue[1]
                    index_val = int(varValue[2]) if varValue[2].isdigit() else varValue[2]

                    if list_var in vars:
                        result = vars[list_var][index_val]
                        vars[varName] = result
                        return                # Standard processing for other stdlib functions
                args_text = ','.join(varValue[1:])
                args = parseArgs(args_text.split(','), func, stdlib, vars)
                if debug: print(f'Using stdlib function {func_name} with {args}')
                try:
                    result = stdlib[func_name](*args)  # Use * to unpack args
                    # Store result directly, not as a list
                    vars[varName] = result
                    print(f"Debug: Set {varName} = '{result}'")  # Debug output
                except Exception as e:
                    if debug:
                        print(f"Error calling {func_name}: {e}")
                    vars[varName] = None

            # For other cases (not stdlib function calls)
            for i in varValue:
                # Is func?
                if i in func:
                    vv.append(runFunc(func, varValue[0], varValue[1:]))
                    break
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

            # Debug the condition before evaluation
            if debug:
                print(f"Evaluating condition: '{cond}'")

            # Special handling for string variable comparison
            if " == " in cond and any(var in cond for var in vars):
                parts = cond.split(" == ")
                left_part = parts[0].strip()
                right_part = parts[1].strip()

                # Get left value
                left_value = vars.get(left_part, left_part)
                if isinstance(left_value, str) and left_value.startswith('"') and left_value.endswith('"'):
                    left_value = left_value.strip('"')

                # Get right value
                right_value = right_part
                if right_part.startswith('"') and right_part.endswith('"'):
                    right_value = right_part.strip('"')

                # Special case for digits
                if str(left_value).isdigit() and right_value.strip('"').isdigit():
                    cond = str(left_value) == right_value.strip('"')
                else:
                    cond = str(left_value) == str(right_value.strip('"'))

                if debug:
                    print(f"String comparison: '{left_value}' == '{right_value}' => {cond}")
            else:
                try:
                    cond = evalExpr(cond, vars)
                except Exception as e:
                    if debug:
                        print(f"Error in condition evaluation: {e}")
                    cond = 0  # Default to false on error

            if debug:
                print(f"Condition result: {cond}")

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
                vars[exposed] = locals()[exposed]
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
              # Special handling for print statements
            if fname == 'print':
                # Handle string with commas (variable references)
                if isinstance(line_1, str) and ',' in line_1:
                    parts = line_1.split(',')
                    args_to_print = []

                    for part in parts:
                        part = part.strip()
                        if part in vars:
                            # It's a variable
                            args_to_print.append(vars[part])
                        elif part.startswith('"') and part.endswith('"'):
                            # It's a string literal
                            args_to_print.append(part.strip('"'))
                        else:
                            # Add as is
                            args_to_print.append(part)

                    print(*args_to_print)
                    continue

                # Handle list of arguments
                elif isinstance(line_1, list):
                    args_to_print = []
                    for arg in line_1:
                        # If it's a variable name
                        if arg in vars:
                            args_to_print.append(vars[arg])
                        # If it's a string literal
                        elif isinstance(arg, str) and arg.startswith('"') and arg.endswith('"'):
                            args_to_print.append(arg.strip('"'))
                        # Otherwise add as is
                        else:
                            args_to_print.append(arg)

                    # Call print with all arguments
                    print(*args_to_print)
                    continue
                # Handle simple cases
                elif isinstance(line_1, str):
                    if '"' in line_1:
                        # Simple string literal print
                        print(line_1.strip('"'))
                        continue
                    elif line_1 in vars:
                        # Single variable print
                        value = vars[line_1]
                        # If the value is a list of one item, extract it
                        if isinstance(value, list) and len(value) == 1:
                            value = value[0]
                        print(value)
                        continue

            # Standard handling for other stdlib functions
            if isinstance(line_1, list):
                line_1 = ','.join(line_1)
            try:
                funcArgs = parseArgs(line_1.split(','), func, stdlib, vars)
                if debug:
                    print(f'Using stdlib function {fname} with {funcArgs}')
                stdlib[fname](*funcArgs)
            except Exception as e:
                print(f"Error calling {fname}: {e}")

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
