"""
JSON to DSL Converter
Transforms structured JSON representation to DSL text format

Why this intermediate step:
---------------------------
Could go directly NL -> DSL, but JSON intermediate provides:
1. Structured validation before text generation
2. Programmatic manipulation (users can edit JSON)
3. Easier testing (JSON is easier to construct in tests)
4. Language independence (JSON is universal)
"""


class JSONToDSL:
    def __init__(self):
        pass
    
    def convert(self, json_data):
        """
        Convert JSON structure to DSL text
        
        Args:
            json_data: Dictionary with 'entry' and 'exit' keys
            
        Returns:
            str: DSL text representation
        """
        dsl_lines = []
        
        # Generate ENTRY section
        dsl_lines.append("ENTRY:")
        if json_data.get('entry'):
            entry_expr = self._build_expression(json_data['entry'])
            dsl_lines.append(f"  {entry_expr}")
        else:
            dsl_lines.append("  TRUE")  # No entry condition
        
        # Empty line
        dsl_lines.append("")
        
        # Generate EXIT section
        dsl_lines.append("EXIT:")
        if json_data.get('exit'):
            exit_expr = self._build_expression(json_data['exit'])
            dsl_lines.append(f"  {exit_expr}")
        else:
            dsl_lines.append("  FALSE")  # No exit condition
        
        return "\n".join(dsl_lines)
    
    def _build_expression(self, conditions):
        """
        Build a single expression from list of conditions
        
        Args:
            conditions: List of condition dictionaries
            
        Returns:
            str: Expression string
        """
        if not conditions:
            return "TRUE"
        
        parts = []
        for i, cond in enumerate(conditions):
            left = self._format_term(cond['left'])
            operator = self._format_operator(cond['operator'])
            right = self._format_term(cond['right'])
            
            expr = f"{left} {operator} {right}"
            parts.append(expr)
            
            # Add connector if not last condition
            if i < len(conditions) - 1:
                connector = cond.get('connector', 'AND')
                parts.append(connector)
        
        return " ".join(parts)
    
    def _format_term(self, term):
        """
            Format a term (could be field, indicator, or literal)
            
            Case normalization:
            - Indicators: UPPERCASE (SMA, RSI, PREV)
            - Fields: lowercase (close, volume)
            - Rationale: Visual distinction improves readability
        """
        if isinstance(term, (int, float)):
            return str(term)
        
        term_str = str(term)
        
        # Check if it's an indicator call (contains parentheses)
        if '(' in term_str and ')' in term_str:
            # Convert to uppercase indicator name
            # e.g., "sma(close, 20)" -> "SMA(close, 20)"
            parts = term_str.split('(', 1)
            indicator_name = parts[0].strip().upper()
            params = parts[1].rstrip(')')
            return f"{indicator_name}({params})"
        
        # Check if it's a prev() call
        if term_str.startswith('prev('):
            parts = term_str.split('(', 1)
            params = parts[1].rstrip(')')
            return f"PREV({params})"
        
        # Check if it's an arithmetic expression
        if any(op in term_str for op in ['+', '-', '*', '/']):
            return term_str
        
        # Otherwise it's a field name
        return term_str.lower()
    
    def _format_operator(self, operator):
        """Format operator to DSL syntax"""
        op_map = {
            '>': '>',
            '<': '<',
            '>=': '>=',
            '<=': '<=',
            '==': '==',
            'crosses_above': 'CROSSES_ABOVE',
            'crosses_below': 'CROSSES_BELOW'
        }
        return op_map.get(operator.lower(), operator.upper())


if __name__ == "__main__":
    # Example usage
    import json
    
    converter = JSONToDSL()
    
    # Example 1
    json_data1 = {
        "entry": [
            {"left": "close", "operator": ">", "right": "sma(close, 20)", "connector": "AND"},
            {"left": "volume", "operator": ">", "right": 1000000}
        ],
        "exit": [
            {"left": "rsi(close, 14)", "operator": "<", "right": 30}
        ]
    }
    
    print("Example 1:")
    print(converter.convert(json_data1))
    print("\n" + "="*50 + "\n")
    
    # Example 2
    json_data2 = {
        "entry": [
            {"left": "close", "operator": "crosses_above", "right": "prev(high, 1)"}
        ],
        "exit": [
            {"left": "rsi(close, 14)", "operator": "<", "right": 30}
        ]
    }
    
    print("Example 2:")
    print(converter.convert(json_data2))