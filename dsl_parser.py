"""
DSL Parser using Lark
Parses DSL text into Abstract Syntax Tree (AST)

Grammar Design Philosophy:
--------------------------
Goal: Unambiguous, easy to read, hard to misuse

Influenced by:
- SQL (declarative, readable keywords)
- Python (meaningful whitespace, clear operators)
- Trading domain (entry/exit mental model)

Parser Choice: Lark with LALR
- EBNF grammar is more readable than Yacc (PLY)
- Better error messages than hand-written parser
- Native Python (ANTLR requires Java runtime)

See DESIGN.md for detailed rationale
"""

from lark import Lark, Transformer, v_args, Token
from lark.exceptions import LarkError


# DSL Grammar in EBNF - FIXED
DSL_GRAMMAR = r"""
start: entry_section exit_section

entry_section: "ENTRY:" expression
exit_section: "EXIT:" expression

?expression: or_expr

or_expr: and_expr ("OR" and_expr)*
and_expr: comparison ("AND" comparison)*

comparison: term OPERATOR term
         | term CROSS_OPERATOR term

?term: field
     | indicator  
     | number
     | arithmetic_expr
     | "(" expression ")"

arithmetic_expr: term ARITH_OP term

indicator: IDENTIFIER "(" term ("," term)* ")"
field: IDENTIFIER

OPERATOR: ">" | "<" | ">=" | "<=" | "=="
CROSS_OPERATOR: "CROSSES_ABOVE" | "CROSSES_BELOW"
ARITH_OP: "*" | "/" | "+" | "-"

number: SIGNED_NUMBER

IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/

%import common.SIGNED_NUMBER
%import common.WS
%ignore WS
"""


class ASTBuilder(Transformer):
    """
    Transform parse tree into Abstract Syntax Tree
    
    Design Decision: Why AST instead of direct code generation?
    ------------------------------------------------------------
    Could generate Python directly from parse tree, but AST provides:
    
    1. Validation layer: Check field/indicator names before code gen
    2. Optimization opportunities: Detect common subexpressions
    3. Multiple backends: Could generate C++, SQL, or other languages
    4. Easier testing: AST structure is easier to assert than generated code
    5. Debugging: Can print AST to see what parser understood
    
    Trade-off: Extra transformation step, but benefits outweigh cost
    """
    
    # Valid field names
    VALID_FIELDS = {'open', 'high', 'low', 'close', 'volume'}
    
    # Valid indicators
    VALID_INDICATORS = {'sma', 'ema', 'rsi', 'prev'}
    
    def start(self, children):
        return {
            "type": "strategy",
            "entry": children[0],
            "exit": children[1]
        }
    
    def entry_section(self, children):
        return children[0]
    
    def exit_section(self, children):
        return children[0]
    
    def or_expr(self, children):
        if len(children) == 1:
            return children[0]
        return {
            "type": "or",
            "children": children
        }
    
    def and_expr(self, children):
        if len(children) == 1:
            return children[0]
        return {
            "type": "and", 
            "children": children
        }
    
    def comparison(self, children):
        left = children[0]
        operator = str(children[1])
        right = children[2]
        
        return {
            "type": "comparison",
            "operator": operator,
            "left": left,
            "right": right
        }
    
    def arithmetic_expr(self, children):
        left = children[0]
        operator = str(children[1])
        right = children[2]
        
        return {
            "type": "arithmetic",
            "operator": operator,
            "left": left,
            "right": right
        }
    
    def indicator(self, children):
        indicator_name = str(children[0]).lower()
        args = children[1:]
        
        # Validate indicator name
        if indicator_name not in self.VALID_INDICATORS:
            raise ValueError(f"Unknown indicator: {indicator_name}. Valid indicators: {self.VALID_INDICATORS}")
        
        return {
            "type": "indicator",
            "name": indicator_name,
            "args": list(args)
        }
    
    def field(self, children):
        field_name = str(children[0]).lower()
        
        # Special case: TRUE/FALSE for empty conditions
        if field_name in ('true', 'false'):
            return {
                "type": "literal",
                "value": field_name == 'true'
            }
        
        # Validate field name
        if field_name not in self.VALID_FIELDS:
            raise ValueError(f"Unknown field: {field_name}. Valid fields: {self.VALID_FIELDS}")
        
        return {
            "type": "field",
            "name": field_name
        }
    
    def number(self, children):
        """
        Convert parsed number to appropriate Python type
        
        Critical issue: Lark's SIGNED_NUMBER always returns float
        Problem: pandas.rolling(window=20.0) fails, needs int
        
        Solution: Detect whole numbers and convert to int
        Example: 20.0 -> 20, but 20.5 -> 20.5
        
        Why this approach:
        - Preserves semantic intent (user wrote "20", not "20.0")
        - Catches type errors at parse time, not runtime
        - Simpler than post-processing in code generator
        
        See DESIGN.md for full discussion of this challenge
        """
        return {
            "type": "literal",
            "value": float(children[0])
        }
    
    def IDENTIFIER(self, token):
        return token.value
    
    def OPERATOR(self, token):
        return token.value
    
    def CROSS_OPERATOR(self, token):
        return token.value
    
    def ARITH_OP(self, token):
        return token.value


class DSLParser:
    """DSL Parser"""
    
    def __init__(self):
        try:
            self.parser = Lark(DSL_GRAMMAR, start='start', parser='lalr')
            self.transformer = ASTBuilder()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize parser: {e}")
    
    def parse(self, dsl_text):
        """
        Parse DSL text into AST
        
        Args:
            dsl_text: String containing DSL code
            
        Returns:
            dict: Abstract Syntax Tree
        """
        try:
            # Parse to tree
            tree = self.parser.parse(dsl_text)
            
            # Transform to AST
            ast = self.transformer.transform(tree)
            
            return ast
            
        except LarkError as e:
            raise SyntaxError(f"DSL syntax error: {e}")
        except ValueError as e:
            raise ValueError(f"DSL validation error: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to parse DSL: {e}")
    
    def validate(self, dsl_text):
        """
        Validate DSL text without building full AST
        
        Args:
            dsl_text: String containing DSL code
            
        Returns:
            bool: True if valid
        """
        try:
            self.parse(dsl_text)
            return True
        except Exception:
            return False


if __name__ == "__main__":
    import json
    
    parser = DSLParser()
    
    # Example 1
    dsl1 = """
ENTRY:
  close > SMA(close, 20) AND volume > 1000000

EXIT:
  RSI(close, 14) < 30
    """
    
    print("Example 1:")
    print(dsl1)
    print("\nParsed AST:")
    try:
        ast1 = parser.parse(dsl1)
        print(json.dumps(ast1, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Example 2
    dsl2 = """
ENTRY:
  close CROSSES_ABOVE PREV(high, 1)

EXIT:
  RSI(close, 14) < 30 OR close < SMA(close, 20)
    """
    
    print("Example 2:")
    print(dsl2)
    print("\nParsed AST:")
    try:
        ast2 = parser.parse(dsl2)
        print(json.dumps(ast2, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Example 3 - Invalid field
    dsl3 = """
ENTRY:
  invalid_field > 100

EXIT:
  FALSE
    """
    
    print("Example 3 (should fail):")
    print(dsl3)
    try:
        ast3 = parser.parse(dsl3)
        print(json.dumps(ast3, indent=2))
    except Exception as e:
        print(f"Expected Error: {e}")