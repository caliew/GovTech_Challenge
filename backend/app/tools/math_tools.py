import json
import math
import logging

logger = logging.getLogger("MathTools")

def calculate_correlation(json_args: str) -> str:
    """
    Computes Pearson's correlation coefficient (r) between two numeric arrays.
    Input must be a JSON string with 'array_x' and 'array_y'.
    Example: '{"array_x": [1, 2, 3], "array_y": [2, 4, 6]}'
    """
    try:
        args = json.loads(json_args)
        x = args.get("array_x")
        y = args.get("array_y")
        
        if not x or not y or len(x) != len(y) or len(x) < 2:
            return "Error: Input arrays must have equal length and at least 2 data points."
            
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_x2 = sum(val**2 for val in x)
        sum_y2 = sum(val**2 for val in y)
        sum_xy = sum(val_x * val_y for val_x, val_y in zip(x, y))
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = math.sqrt((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))
        
        if denominator == 0:
            return "0.0 (No variation in one or both datasets)"
            
        r = numerator / denominator
        return f"{r:.4f}"
    except Exception as e:
        return f"Error: Malformed JSON arguments: {str(e)}"

def calculate_growth_rate(json_args: str) -> str:
    """
    Computes the Compound Annual Growth Rate (CAGR) or year-on-year growth rates.
    Input must be a JSON string with 'start_value', 'end_value', and 'periods'.
    Example: '{"start_value": 6500, "end_value": 8200, "periods": 4}'
    """
    try:
        args = json.loads(json_args)
        start = float(args.get("start_value"))
        end = float(args.get("end_value"))
        periods = int(args.get("periods"))
        
        if start <= 0 or end <= 0 or periods <= 0:
            return "Error: Start and end values must be positive, and periods greater than zero."
            
        cagr = (end / start) ** (1 / periods) - 1
        return f"{cagr * 100:.2f}%"
    except Exception as e:
        return f"Error: Malformed JSON arguments: {str(e)}"
