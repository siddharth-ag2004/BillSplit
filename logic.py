# logic.py

import json
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Tuple


class CalculationError(Exception):
    """Custom exception for calculation errors."""

    pass


def safe_decimal_eval(expression: str) -> Decimal:
    """
    Safely evaluates a string expression and returns it as a Decimal.
    Raises CalculationError for invalid expressions.
    """
    if not expression:
        return Decimal(0)
    try:
        # Using eval with limited scope for simple arithmetic (e.g., "15/2")
        return Decimal(eval(expression, {"__builtins__": None}, {}))
    except Exception:
        raise CalculationError(f"Invalid expression: {expression}")


def load_people_from_file(filepath: str) -> List[str]:
    """
    Loads a list of people from a JSON file.
    Raises FileNotFoundError or json.JSONDecodeError on failure.
    """
    with open(filepath, "r") as f:
        return json.load(f)


def calculate_split_bill(
    person_amounts: List[Tuple[str, Decimal]], other_charges: Decimal
) -> Dict:
    """
    Performs the bill splitting calculation.

    Args:
        person_amounts: A list of tuples, where each tuple is (person_name, amount).
        other_charges: Additional charges to be split.

    Returns:
        A dictionary containing the calculation results.
    """
    amounts = [amount for _, amount in person_amounts]
    total = sum(amounts)

    if total == 0:
        if other_charges > 0 and person_amounts:
            num_people = len(person_amounts)
            split_other_charges = other_charges / num_people
            final_amounts = [(name, split_other_charges) for name, _ in person_amounts]
            return {
                "subtotal": Decimal(0),
                "grand_total": other_charges,
                "final_amounts": final_amounts,
                "is_equal_split": True,
            }
        else:
            return {}  # Signifies nothing to calculate

    weights = [x / total for x in amounts]
    final_amounts = []
    for i, (name, amount) in enumerate(person_amounts):
        final_amount = amount + other_charges * weights[i]
        final_amounts.append((name, final_amount))

    return {
        "subtotal": total,
        "grand_total": total + other_charges,
        "final_amounts": final_amounts,
        "is_equal_split": False,
    }
