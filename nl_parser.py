"""
Natural Language Parser using Groq API
Converts natural language trading rules to structured JSON

Design Decision: LLM-based parsing vs Rule-based parsing
---------------------------------------------------------
Considered three approaches:
1. Rule-based (regex + keyword matching) - Rejected: brittle
2. Spacy NLP + dependency parsing - Rejected: complex maintenance
3. LLM-based (Groq API) - CHOSEN: handles linguistic variation naturally

Trade-off accepted: API dependency for better UX
"""

import json
import re
import os
from groq import Groq

class NLParser:
    def __init__(self, api_key=None):
        """Initialize Groq client"""
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment or parameters")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "openai/gpt-oss-120b"
    
    def parse(self, natural_language_input):
        """
            Convert natural language to structured JSON
            
            Prompt Engineering Strategy:
            ----------------------------
            1. Explicit schema definition (reduces hallucination)
            2. Multiple examples (few-shot learning)
            3. Output format constraints ("ONLY valid JSON")
            4. Edge case handling (empty conditions)
            
            Temperature setting: 0.1 (not 0)
            - 0.0 can cause repetitive/deterministic failures
            - 0.1 allows slight variation for robustness
            - Still low enough for consistency
        """
        system_prompt = """You are a trading strategy parser. Convert natural language trading rules into structured JSON.

Output JSON schema:
{
  "entry": [
    {
      "left": "field or indicator expression",
      "operator": "comparison operator",
      "right": "value or expression",
      "connector": "AND or OR (optional, omit for last condition)"
    }
  ],
  "exit": [
    {
      "left": "field or indicator expression", 
      "operator": "comparison operator",
      "right": "value or expression",
      "connector": "AND or OR (optional)"
    }
  ]
}

Available fields: open, high, low, close, volume

Available indicators (use this exact format):
- sma(field, period) - Simple Moving Average
- ema(field, period) - Exponential Moving Average  
- rsi(field, period) - Relative Strength Index

Available operators: >, <, >=, <=, ==, crosses_above, crosses_below

Special expressions:
- prev(field, N) - Value N days ago (e.g., prev(high, 1) for yesterday's high)
- For percentage comparisons, convert to decimal (e.g., "30 percent" becomes 0.30)

Rules:
1. Use lowercase for field names
2. Use exact indicator syntax: indicator_name(field, period)
3. For "crosses above/below", use operator "crosses_above" or "crosses_below"
4. Convert percentages to decimals
5. Return ONLY valid JSON, no markdown, no explanations
6. If entry or exit is not specified, use empty array []

Examples:

Input: "Buy when close is above 20-day moving average and volume is above 1 million"
Output:
{
  "entry": [
    {"left": "close", "operator": ">", "right": "sma(close, 20)", "connector": "AND"},
    {"left": "volume", "operator": ">", "right": 1000000}
  ],
  "exit": []
}

Input: "Enter when price crosses above yesterday's high. Exit when RSI(14) is below 30"
Output:
{
  "entry": [
    {"left": "close", "operator": "crosses_above", "right": "prev(high, 1)"}
  ],
  "exit": [
    {"left": "rsi(close, 14)", "operator": "<", "right": 30}
  ]
}

Input: "Trigger entry when volume increases by more than 30 percent compared to last week"
Output:
{
  "entry": [
    {"left": "volume", "operator": ">", "right": "prev(volume, 7) * 1.30"}
  ],
  "exit": []
}
"""

        user_prompt = f"""Parse this trading rule into JSON:

{natural_language_input}

Return only the JSON output, no explanations."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            raw_output = response.choices[0].message.content
            
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
            if not json_match:
                raise ValueError(f"No valid JSON found in response: {raw_output}")
            
            parsed_json = json.loads(json_match.group())
            
            # Validate structure
            self._validate_json(parsed_json)
            
            return parsed_json
            
        except Exception as e:
            raise RuntimeError(f"Failed to parse natural language: {str(e)}")
    
    def _validate_json(self, data):
        """Validate the structure of parsed JSON"""
        if not isinstance(data, dict):
            raise ValueError("Output must be a dictionary")
        
        if 'entry' not in data:
            raise ValueError("Missing 'entry' key")
        
        if 'exit' not in data:
            raise ValueError("Missing 'exit' key")
        
        if not isinstance(data['entry'], list):
            raise ValueError("'entry' must be a list")
        
        if not isinstance(data['exit'], list):
            raise ValueError("'exit' must be a list")
        
        # Validate each condition
        for section in ['entry', 'exit']:
            for condition in data[section]:
                if not isinstance(condition, dict):
                    raise ValueError(f"Each condition in '{section}' must be a dict")
                
                required = ['left', 'operator', 'right']
                for key in required:
                    if key not in condition:
                        raise ValueError(f"Condition missing required key: {key}")


if __name__ == "__main__":
    # Example usage
    parser = NLParser()
    
    examples = [
        "Buy when the close price is above the 20-day moving average and volume is above 1 million.",
        "Enter when price crosses above yesterday's high.",
        "Exit when RSI(14) is below 30.",
        "Trigger entry when volume increases by more than 30 percent compared to last week."
    ]
    
    for example in examples:
        print(f"\nInput: {example}")
        try:
            result = parser.parse(example)
            print(f"Output: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"Error: {e}")