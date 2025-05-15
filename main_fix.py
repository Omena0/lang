"""
Revamped interpreter for the 'lang' programming language.
This implementation uses a proper lexer-parser-interpreter architecture
while maintaining compatibility with the original language features.
"""

import os
import sys
import importlib.util
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union, Callable


# ---- LEXER ----
class TokenType(Enum):
    """Token types for the lexer."""
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()
    OPERATOR = auto()
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    COMMA = auto()
    EQUALS = auto()
    EOF = auto()


class Token:
    """Represents a token in the source code."""
    def __init__(self, token_type: TokenType, value: str, line: int):
        self.type = token_type
        self.value = value
        self.line = line

    def __str__(self) -> str:
        return f"Token({self.type}, '{self.value}', line {self.line})"


class Lexer:
    """Converts source code to tokens."""
    
    # Valid operators
    OPERATORS = {'+', '-', '*', '/', '%', '^', '&', '|', '!', '<', '>', '=', '<=', '>=', '==', '!=', '=!'}

    def __init__(self, source: str):
        self.source = self._preprocess_source(source)
        self.tokens = []
        self.start = 0
        self.current = 0
        self.line = 1
    
    def _preprocess_source(self, source: str) -> str:
        """Remove comments and normalize whitespace."""
        lines = []
        for line in source.splitlines():
            # Remove comments
            if '//' in line:
                line = line.split('//', 1)[0]
            
            # Skip empty lines
            if not line.strip():
                continue
            
            # Replace true with 1 and false with 0
            line = line.replace(' true ', ' 1 ').replace(' false ', ' 0 ')
            # Handle cases where true/false are at the beginning or end of the line
            line = line.replace(' true', ' 1').replace(' false', ' 0')
            line = line.replace('true ', '1 ').replace('false ', '0 ')
            # Handle cases where true/false are the entire line
            line = line.replace('true', '1').replace('false', '0')
            
            lines.append(line)
            
        # Return processed source with normalized spaces
        result = '\n'.join(lines)
        # Add spaces around parentheses and braces for easier lexing
        result = result.replace('(', ' ( ').replace(')', ' ) ')
        result = result.replace('{', ' { ').replace('}', ' } ')
        # Normalize whitespace
        while '  ' in result:
            result = result.replace('  ', ' ')
        return result
    
    def scan_tokens(self) -> List[Token]:
        """Scan the source code and return a list of tokens."""
        while not self._is_at_end():
            self.start = self.current
            self._scan_token()
        
        self.tokens.append(Token(TokenType.EOF, "", self.line))
        return self.tokens
    
    def _scan_token(self) -> None:
        """Scan a single token."""
        c = self._advance()
        if c.isspace():
            # Handle line breaks for line counting
            if c == '\n':
                self.line += 1
            return
            
        if c.isdigit():
            self._number()
        elif c.isalpha() or c == '_':
            self._identifier()
        elif c == '"' or c == "'":
            self._string(c)  # Pass the quote type to _string
        elif c == '(':
            self._add_token(TokenType.LEFT_PAREN)
        elif c == ')':
            self._add_token(TokenType.RIGHT_PAREN)
        elif c == '{':
            self._add_token(TokenType.LEFT_BRACE)
        elif c == '}':
            self._add_token(TokenType.RIGHT_BRACE)
        elif c == ',':
            self._add_token(TokenType.COMMA)
        elif c == '=':
            if self._match('='):
                self._add_token(TokenType.OPERATOR, '==')
            else:
                self._add_token(TokenType.EQUALS)
        elif c in '+-*/^%':
            self._add_token(TokenType.OPERATOR, c)
        elif c == '<':
            if self._match('='):
                self._add_token(TokenType.OPERATOR, '<=')
            else:
                self._add_token(TokenType.OPERATOR, '<')
        elif c == '>':
            if self._match('='):
                self._add_token(TokenType.OPERATOR, '>=')
            else:
                self._add_token(TokenType.OPERATOR, '>')
        elif c == '!':
            if self._match('='):
                self._add_token(TokenType.OPERATOR, '!=')
            else:
                self._add_token(TokenType.OPERATOR, '!')
        elif c == '&':
            self._add_token(TokenType.OPERATOR, '&')
        elif c == '|':
            self._add_token(TokenType.OPERATOR, '|')
        else:
            raise SyntaxError(f"Unexpected character: {c} at line {self.line}")
    
    def _is_at_end(self) -> bool:
        """Check if we've reached the end of the source."""
        return self.current >= len(self.source)
    
    def _advance(self) -> str:
        """Advance the current position and return the character."""
        c = self.source[self.current]
        self.current += 1
        return c
    
    def _peek(self) -> str:
        """Return the current character without advancing."""
        if self._is_at_end():
            return '\0'
        return self.source[self.current]
    
    def _peek_next(self) -> str:
        """Return the next character without advancing."""
        if self.current + 1 >= len(self.source):
            return '\0'
        return self.source[self.current + 1]
    
    def _match(self, expected: str) -> bool:
        """Match the current character with the expected one."""
        if self._is_at_end() or self.source[self.current] != expected:
            return False
        self.current += 1
        return True
    
    def _add_token(self, token_type: TokenType, value: str = None) -> None:
        """Add a token to the list."""
        if value is None:
            value = self.source[self.start:self.current]
        self.tokens.append(Token(token_type, value, self.line))
      def _string(self, quote_char: str) -> None:
        """Process a string literal.
        
        Args:
            quote_char: The quote character used for the string (either ' or ")
        """
        while self._peek() != quote_char and not self._is_at_end():
            if self._peek() == '\n':
                self.line += 1
            self._advance()
        
        if self._is_at_end():
            raise SyntaxError(f"Unterminated string at line {self.line}")
        
        # Consume the closing quote
        self._advance()
        
        # The value is the string without the quotes
        value = self.source[self.start + 1:self.current - 1]
        self._add_token(TokenType.STRING, value)
    
    def _number(self) -> None:
        """Process a number literal."""
        while self._peek().isdigit():
            self._advance()
        
        # Look for a decimal part
        if self._peek() == '.' and self._peek_next().isdigit():
            # Consume the '.'
            self._advance()
            
            while self._peek().isdigit():
                self._advance()
        
        value = self.source[self.start:self.current]
        self._add_token(TokenType.NUMBER, value)
    
    def _identifier(self) -> None:
        """Process an identifier."""
        while self._peek().isalnum() or self._peek() == '_':
            self._advance()
        
        text = self.source[self.start:self.current]
        self._add_token(TokenType.IDENTIFIER, text)


# ---- AST NODES ----

class Node:
    """Base class for AST nodes."""
    pass


class Program(Node):
    """Represents a program."""
    def __init__(self, functions: Dict[str, 'FunctionDecl']):
        self.functions = functions


class FunctionDecl(Node):
    """Represents a function declaration."""
    def __init__(self, name: str, params: List[str], body: List['Statement']):
        self.name = name
        self.params = params
        self.body = body
        self.variables = {}  # Function's local variables


class Statement(Node):
    """Base class for statements."""
    pass


class ExpressionStmt(Statement):
    """Represents an expression statement."""
    def __init__(self, expression: 'Expression'):
        self.expression = expression


class VarDeclarationStmt(Statement):
    """Represents a variable declaration statement."""
    def __init__(self, name: str, initializer: 'Expression'):
        self.name = name
        self.initializer = initializer


class IfStatement(Statement):
    """Represents an if statement."""
    def __init__(self, condition: 'Expression', then_branch: List[Statement], 
                 else_branch: List[Statement] = None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch or []


class ReturnStatement(Statement):
    """Represents a return statement."""
    def __init__(self, value: 'Expression'):
        self.value = value


class ImportStatement(Statement):
    """Represents an import statement."""
    def __init__(self, path: str):
        self.path = path


class ExposeStatement(Statement):
    """Represents an expose statement."""
    def __init__(self, name: str):
        self.name = name


class Expression(Node):
    """Base class for expressions."""
    pass


class LiteralExpr(Expression):
    """Represents a literal expression (number, string, etc.)."""
    def __init__(self, value: Any):
        self.value = value


class VariableExpr(Expression):
    """Represents a variable expression."""
    def __init__(self, name: str):
        self.name = name


class BinaryExpr(Expression):
    """Represents a binary expression (e.g., a + b)."""
    def __init__(self, left: Expression, operator: str, right: Expression):
        self.left = left
        self.operator = operator
        self.right = right


class UnaryExpr(Expression):
    """Represents a unary expression (e.g., !a)."""
    def __init__(self, operator: str, operand: Expression):
        self.operator = operator
        self.operand = operand


class CallExpr(Expression):
    """Represents a function call expression."""
    def __init__(self, callee: str, arguments: List[Expression]):
        self.callee = callee
        self.arguments = arguments


# ---- PARSER ----

class Parser:
    """Parses tokens into an AST."""
    
    def __init__(self, tokens: List[Token], debug: bool = False):
        self.tokens = tokens
        self.current = 0
        self.debug = debug
    
    def parse(self) -> Program:
        """Parse the tokens into an AST."""
        functions = {}
        
        # Parse top-level declarations
        while not self._is_at_end():
            if self._check(TokenType.IDENTIFIER) and self._peek().value == "fn":
                self._advance()  # Consume 'fn'
                func = self._function_declaration()
                functions[func.name] = func
            else:
                # Non-function statements go into main
                if "main" not in functions:
                    functions["main"] = FunctionDecl("main", [], [])
                
                # Add statement to main
                functions["main"].body.append(self._statement())
        
        # Ensure main exists
        if "main" not in functions:
            functions["main"] = FunctionDecl("main", [], [])
        
        return Program(functions)
    
    def _function_declaration(self) -> FunctionDecl:
        """Parse a function declaration."""
        name = self._consume(TokenType.IDENTIFIER, "Expected function name.").value
        
        params = []
        
        # Parse parameters
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after function name.")
        
        if not self._check(TokenType.RIGHT_PAREN):
            while True:
                params.append(self._consume(TokenType.IDENTIFIER, "Expected parameter name.").value)
                
                if not self._match(TokenType.COMMA):
                    break
        
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after parameters.")
        
        # Parse function body
        body = []
        self._consume(TokenType.LEFT_BRACE, "Expected '{' before function body.")
        
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            body.append(self._statement())
        
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after function body.")
        
        return FunctionDecl(name, params, body)
    
    def _statement(self) -> Statement:
        """Parse a statement."""
        if self._check(TokenType.IDENTIFIER):
            identifier = self._peek().value
            
            if identifier == "let":
                self._advance()  # Consume 'let'
                return self._var_declaration()
            elif identifier == "if":
                self._advance()  # Consume 'if'
                return self._if_statement()
            elif identifier == "return":
                self._advance()  # Consume 'return'
                return self._return_statement()
            elif identifier == "import":
                self._advance()  # Consume 'import'
                return self._import_statement()
            elif identifier == "expose":
                self._advance()  # Consume 'expose'
                return self._expose_statement()
        
        # Default: expression statement
        return ExpressionStmt(self._expression())
    
    def _var_declaration(self) -> VarDeclarationStmt:
        """Parse a variable declaration."""
        name = self._consume(TokenType.IDENTIFIER, "Expected variable name.").value
        
        initializer = None
        if self._match(TokenType.EQUALS):
            initializer = self._expression()
        
        return VarDeclarationStmt(name, initializer)
    
    def _if_statement(self) -> IfStatement:
        """Parse an if statement."""
        # Optional parentheses around condition
        has_paren = self._match(TokenType.LEFT_PAREN)
        condition = self._expression()
        if has_paren:
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after if condition.")
        
        # Parse then branch
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after if condition.")
        then_branch = []
        
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            then_branch.append(self._statement())
        
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after if branch.")
        
        # Parse optional else branch
        else_branch = []
        if self._check(TokenType.IDENTIFIER) and self._peek().value == "else":
            self._advance()  # Consume 'else'
            
            # Check for "else if" construct
            if self._check(TokenType.IDENTIFIER) and self._peek().value == "if":
                self._advance()  # Consume 'if'
                # Create an else branch with a single nested if statement
                else_branch.append(self._if_statement())
            else:
                # Regular else branch
                self._consume(TokenType.LEFT_BRACE, "Expected '{' after else.")
                
                while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
                    else_branch.append(self._statement())
                
                self._consume(TokenType.RIGHT_BRACE, "Expected '}' after else branch.")
        
        return IfStatement(condition, then_branch, else_branch)
    
    def _return_statement(self) -> ReturnStatement:
        """Parse a return statement."""
        value = self._expression()
        return ReturnStatement(value)
    
    def _import_statement(self) -> ImportStatement:
        """Parse an import statement."""
        path = self._consume(TokenType.STRING, "Expected file path string.").value
        return ImportStatement(path)
    
    def _expose_statement(self) -> ExposeStatement:
        """Parse an expose statement."""
        name = self._consume(TokenType.IDENTIFIER, "Expected exposed name.").value
        return ExposeStatement(name)
    
    def _expression(self) -> Expression:
        """Parse an expression."""
        return self._equality()
    
    def _equality(self) -> Expression:
        """Parse an equality expression."""
        expr = self._comparison()
        
        while self._match(TokenType.OPERATOR, "==") or self._match(TokenType.OPERATOR, "!=") or self._match(TokenType.OPERATOR, "=!"):
            operator = self._previous().value
            right = self._comparison()
            expr = BinaryExpr(expr, operator, right)
        
        return expr
    
    def _comparison(self) -> Expression:
        """Parse a comparison expression."""
        expr = self._term()
        
        while (self._match(TokenType.OPERATOR, "<") or 
               self._match(TokenType.OPERATOR, ">") or 
               self._match(TokenType.OPERATOR, "<=") or 
               self._match(TokenType.OPERATOR, ">=")):
            operator = self._previous().value
            right = self._term()
            expr = BinaryExpr(expr, operator, right)
        
        return expr
    
    def _term(self) -> Expression:
        """Parse a term expression."""
        expr = self._factor()
        
        while self._match(TokenType.OPERATOR, "+") or self._match(TokenType.OPERATOR, "-") or self._match(TokenType.OPERATOR, "|") or self._match(TokenType.OPERATOR, "&"):
            operator = self._previous().value
            right = self._factor()
            expr = BinaryExpr(expr, operator, right)
        
        return expr
    
    def _factor(self) -> Expression:
        """Parse a factor expression."""
        expr = self._unary()
        
        while self._match(TokenType.OPERATOR, "*") or self._match(TokenType.OPERATOR, "/") or self._match(TokenType.OPERATOR, "%"):
            operator = self._previous().value
            right = self._unary()
            expr = BinaryExpr(expr, operator, right)
        
        return expr
    
    def _unary(self) -> Expression:
        """Parse a unary expression."""
        if self._match(TokenType.OPERATOR, "!") or self._match(TokenType.OPERATOR, "-"):
            operator = self._previous().value
            right = self._unary()
            return UnaryExpr(operator, right)
        
        return self._power()
    
    def _power(self) -> Expression:
        """Parse a power expression."""
        expr = self._primary()
        
        if self._match(TokenType.OPERATOR, "^"):
            operator = self._previous().value
            right = self._unary()  # Right-associative
            return BinaryExpr(expr, operator, right)
        
        return expr
    
    def _primary(self) -> Expression:
        """Parse a primary expression."""
        if self._match(TokenType.NUMBER):
            value = self._previous().value
            if '.' in value:
                return LiteralExpr(float(value))
            return LiteralExpr(int(value))
        
        if self._match(TokenType.STRING):
            return LiteralExpr(self._previous().value)
        
        if self._match(TokenType.IDENTIFIER):
            name = self._previous().value
            
            # Check if it's a function call
            if self._match(TokenType.LEFT_PAREN):
                arguments = []
                
                if not self._check(TokenType.RIGHT_PAREN):
                    while True:
                        arguments.append(self._expression())
                        
                        if not self._match(TokenType.COMMA):
                            break
                
                self._consume(TokenType.RIGHT_PAREN, "Expected ')' after arguments.")
                
                return CallExpr(name, arguments)
            
            return VariableExpr(name)
        
        if self._match(TokenType.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after expression.")
            return expr
        
        raise SyntaxError(f"Unexpected token: {self._peek()}")
    
    def _match(self, *types_and_values) -> bool:
        """Match the current token with any of the given types and values."""
        if len(types_and_values) == 1:
            # Just match type
            if self._check(types_and_values[0]):
                self._advance()
                return True
        elif len(types_and_values) == 2:
            # Match type and value
            if self._check(types_and_values[0]) and self._peek().value == types_and_values[1]:
                self._advance()
                return True
        
        return False
    
    def _check(self, token_type: TokenType) -> bool:
        """Check if the current token matches the given type."""
        if self._is_at_end():
            return False
        return self._peek().type == token_type
    
    def _advance(self) -> Token:
        """Advance the current position and return the token."""
        if not self._is_at_end():
            self.current += 1
        return self._previous()
    
    def _is_at_end(self) -> bool:
        """Check if we've reached the end of the tokens."""
        return self._peek().type == TokenType.EOF
    
    def _peek(self) -> Token:
        """Return the current token without advancing."""
        return self.tokens[self.current]
    
    def _previous(self) -> Token:
        """Return the previous token."""
        return self.tokens[self.current - 1]
    
    def _consume(self, token_type: TokenType, error_message: str) -> Token:
        """Consume the current token if it matches the given type."""
        if self._check(token_type):
            return self._advance()
        
        raise SyntaxError(f"{error_message} at line {self._peek().line}")


# ---- INTERPRETER ----

class Environment:
    """Represents a variable environment."""
    
    def __init__(self, enclosing: 'Environment' = None):
        self.values: Dict[str, Any] = {}
        self.enclosing = enclosing
    
    def define(self, name: str, value: Any) -> None:
        """Define a variable in the current environment."""
        self.values[name] = value
    
    def get(self, name: str) -> Any:
        """Get a variable's value from the environment."""
        if name in self.values:
            return self.values[name]
        
        if self.enclosing:
            return self.enclosing.get(name)
        
        raise UnboundLocalError(f"Variable '{name}' is not defined.")
    
    def assign(self, name: str, value: Any) -> None:
        """Assign a new value to an existing variable."""
        if name in self.values:
            self.values[name] = value
            return
        
        if self.enclosing:
            self.enclosing.assign(name, value)
            return
        
        raise UnboundLocalError(f"Variable '{name}' is not defined.")
    
    def copy(self) -> 'Environment':
        """Create a copy of the current environment."""
        env = Environment(self.enclosing)
        env.values = self.values.copy()
        return env


class Function:
    """Represents a user-defined function."""
    
    def __init__(self, declaration: FunctionDecl, closure: Environment):
        self.declaration = declaration
        self.closure = closure
    
    def call(self, interpreter: 'Interpreter', arguments: List[Any]) -> Any:
        """Call the function with the given arguments."""
        environment = Environment(self.closure)
        
        # Bind arguments to parameters
        for i in range(len(self.declaration.params)):
            environment.define(self.declaration.params[i], arguments[i])
        
        # Execute the function body
        result = None
        for stmt in self.declaration.body:
            try:
                result = interpreter.execute_statement(stmt, environment)
            except ReturnValue as return_value:
                return return_value.value
        
        return result


class StdlibFunction:
    """Represents a standard library function."""
    
    def __init__(self, python_func: Callable):
        self.python_func = python_func
    
    def call(self, interpreter: 'Interpreter', arguments: List[Any]) -> Any:
        """Call the stdlib function with the given arguments."""
        return self.python_func(*arguments)


class ReturnValue(Exception):
    """Exception used to handle return statements."""
    
    def __init__(self, value: Any):
        self.value = value
        super().__init__(self)


class Interpreter:
    """Executes the AST."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.globals = Environment()
        self.environment = self.globals
        self.functions: Dict[str, Union[Function, StdlibFunction]] = {}
        self.stdlib: Dict[str, Callable] = {}
        
        # Load the standard library
        self._load_stdlib()
    
    def _load_stdlib(self, path: str = 'stdlib') -> None:
        """Load the standard library functions."""
        for file in os.listdir(path):
            if not file.endswith('.py'):
                continue
            if not os.path.isfile(os.path.join(path, file)):
                continue

            # Import module
            module_name = file.split('.')[0]
            spec = importlib.util.spec_from_file_location(
                module_name, os.path.join(path, file))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get stdlib functions
            for attr_name in dir(module):
                if not attr_name.startswith('std_'):
                    continue
                
                # Register stdlib function
                func_name = attr_name[4:]  # Remove 'std_' prefix
                self.stdlib[func_name] = getattr(module, attr_name)
                self.functions[func_name] = StdlibFunction(getattr(module, attr_name))
                
                if self.debug:
                    print(f"Loaded stdlib function: {func_name}")
    
    def interpret(self, program: Program) -> Any:
        """Interpret the program."""
        # Create function objects
        for name, func_decl in program.functions.items():
            self.functions[name] = Function(func_decl, self.environment)
        
        # Call the main function
        if "main" not in self.functions:
            raise NameError("No 'main' function defined.")
        
        return self.functions["main"].call(self, [])
    
    def execute_statement(self, stmt: Statement, env: Environment) -> Any:
        """Execute a statement."""
        if isinstance(stmt, ExpressionStmt):
            return self.evaluate_expression(stmt.expression, env)
        
        elif isinstance(stmt, VarDeclarationStmt):
            value = None
            if stmt.initializer:
                value = self.evaluate_expression(stmt.initializer, env)
            env.define(stmt.name, value)
            return None
        
        elif isinstance(stmt, IfStatement):
            condition = self.evaluate_expression(stmt.condition, env)
            
            # Convert to boolean (0/1)
            if isinstance(condition, (int, float)):
                condition = int(condition != 0)
            elif isinstance(condition, bool):
                condition = int(condition)
            elif isinstance(condition, str):
                condition = int(bool(condition))
            
            if condition:
                for s in stmt.then_branch:
                    result = self.execute_statement(s, env)
                    if isinstance(result, ReturnValue):
                        return result
            else:
                for s in stmt.else_branch:
                    result = self.execute_statement(s, env)
                    if isinstance(result, ReturnValue):
                        return result
            
            return None
        
        elif isinstance(stmt, ReturnStatement):
            value = self.evaluate_expression(stmt.value, env)
            raise ReturnValue(value)
        
        elif isinstance(stmt, ImportStatement):
            # Read file and parse it
            path = stmt.path
            try:
                with open(path, 'r') as file:
                    source = file.read()
                
                # Create lexer and parser
                lexer = Lexer(source)
                tokens = lexer.scan_tokens()
                parser = Parser(tokens, self.debug)
                imported_program = parser.parse()
                
                # Add functions to interpreter
                for name, func_decl in imported_program.functions.items():
                    self.functions[name] = Function(func_decl, self.environment)
                
                if self.debug:
                    print(f"Imported functions from {path}: {list(imported_program.functions.keys())}")
            
            except Exception as e:
                raise ImportError(f"Failed to import {path}: {e}")
            
            return None
        
        elif isinstance(stmt, ExposeStatement):
            # Expose Python function or variable
            name = stmt.name
            if name in globals():
                self.functions[name] = StdlibFunction(globals()[name])
            elif name in locals():
                self.functions[name] = StdlibFunction(locals()[name])
            elif name in dir(__builtins__):
                self.functions[name] = StdlibFunction(getattr(__builtins__, name))
            else:
                raise NameError(f"Cannot expose '{name}': not defined.")
            
            return None
    
    def evaluate_expression(self, expr: Expression, env: Environment) -> Any:
        """Evaluate an expression."""
        if isinstance(expr, LiteralExpr):
            return expr.value
        
        elif isinstance(expr, VariableExpr):
            return env.get(expr.name)
        
        elif isinstance(expr, BinaryExpr):
            left = self.evaluate_expression(expr.left, env)
            right = self.evaluate_expression(expr.right, env)
              # Handle string values
            if isinstance(left, str):
                if (left.startswith('"') and left.endswith('"')) or (left.startswith("'") and left.endswith("'")):
                    left = left[1:-1]
            if isinstance(right, str):
                if (right.startswith('"') and right.endswith('"')) or (right.startswith("'") and right.endswith("'")):
                    right = right[1:-1]
            
            # Perform operation
            if expr.operator == "+":
                if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    return left + right
                return str(left) + str(right)
            
            elif expr.operator == "-":
                return float(left) - float(right)
            
            elif expr.operator == "*":
                return float(left) * float(right)
            
            elif expr.operator == "/":
                return float(left) / float(right)
            
            elif expr.operator == "%":
                return float(left) % float(right)
            
            elif expr.operator == "^":
                return float(left) ** float(right)
            
            elif expr.operator == "&":
                return bool(left) and bool(right)
            
            elif expr.operator == "|":
                return bool(left) or bool(right)
            
            elif expr.operator == "<":
                return float(left) < float(right)
            
            elif expr.operator == ">":
                return float(left) > float(right)
            
            elif expr.operator == "<=":
                return float(left) <= float(right)
            
            elif expr.operator == ">=":
                return float(left) >= float(right)
            
            elif expr.operator == "==":
                return left == right
            
            elif expr.operator in ("!=", "=!"):
                return left != right
        
        elif isinstance(expr, UnaryExpr):
            operand = self.evaluate_expression(expr.operand, env)
            
            if expr.operator == "!":
                return not bool(operand)
            
            elif expr.operator == "-":
                return -float(operand)
        
        elif isinstance(expr, CallExpr):
            callee = expr.callee
            arguments = [self.evaluate_expression(arg, env) for arg in expr.arguments]
            
            # Find function
            if callee in self.functions:
                function = self.functions[callee]
                return function.call(self, arguments)
            else:
                raise NameError(f"Function '{callee}' is not defined.")
        
        raise RuntimeError(f"Unknown expression type: {expr.__class__.__name__}")


# ---- MAIN FUNCTION ----

def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python main_new.py <filename>")
        sys.exit(1)
    
    # Read source file
    try:
        with open(sys.argv[1], 'r') as file:
            source = file.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    debug = False  # Change to True for debug output
    
    try:
        # Create lexer and parser
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        
        if debug:
            print("TOKENS:")
            for token in tokens:
                print(token)
            print()
        
        parser = Parser(tokens, debug)
        program = parser.parse()
        
        # Create interpreter and run
        interpreter = Interpreter(debug)
        result = interpreter.interpret(program)
        
        # Exit with the result code
        if result is None:
            sys.exit(0)
        
        try:
            exit_code = int(result)
        except ValueError:
            exit_code = 0
        
        sys.exit(exit_code)
    
    except Exception as e:
        print(f"Error: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
