"""
Condition Evaluator

Evaluates conditions against data to determine routing in workflows.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ConditionOperator(str, Enum):
    """Condition operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    BETWEEN = "between"


@dataclass
class Condition:
    """Condition definition."""
    operator: ConditionOperator
    value: Optional[str] = None
    valueMin: Optional[str] = None
    valueMax: Optional[str] = None


@dataclass
class ConditionResult:
    """Result of condition evaluation."""
    success: bool
    matched_index: Optional[int] = None  # Index of matched condition (None for else)
    matched_condition: Optional[Condition] = None
    error: Optional[str] = None


class ConditionEvaluator:
    """Evaluates conditions against data."""
    
    def __init__(self):
        """Initialize condition evaluator."""
        pass
    
    def evaluate(
        self,
        data: Any,
        conditions: List[Condition],
        field_name: Optional[str] = None
    ) -> ConditionResult:
        """
        Evaluate conditions against data.
        
        Args:
            data: Data to evaluate (can be dict, string, number, etc.)
            conditions: List of conditions to evaluate
            field_name: Optional field name to extract from data dict
            
        Returns:
            ConditionResult with matched condition index or None for else
        """
        try:
            # Extract value from data if field_name provided
            if field_name and isinstance(data, dict):
                value = data.get(field_name)
            else:
                value = data
            
            # Evaluate each condition in order
            for index, condition in enumerate(conditions):
                if self._evaluate_condition(value, condition):
                    return ConditionResult(
                        success=True,
                        matched_index=index,
                        matched_condition=condition
                    )
            
            # No condition matched - return else (None index)
            return ConditionResult(
                success=True,
                matched_index=None,
                matched_condition=None
            )
            
        except Exception as e:
            return ConditionResult(
                success=False,
                error=f"Condition evaluation failed: {str(e)}"
            )
    
    def _evaluate_condition(self, value: Any, condition: Condition) -> bool:
        """
        Evaluate a single condition.
        
        Args:
            value: Value to evaluate
            condition: Condition to check
            
        Returns:
            True if condition matches, False otherwise
        """
        operator = condition.operator
        
        # Convert value to string for comparison
        value_str = str(value) if value is not None else ""
        
        if operator == ConditionOperator.EQUALS:
            return value_str.lower() == (condition.value or "").lower()
        
        elif operator == ConditionOperator.NOT_EQUALS:
            return value_str.lower() != (condition.value or "").lower()
        
        elif operator == ConditionOperator.CONTAINS:
            return (condition.value or "").lower() in value_str.lower()
        
        elif operator == ConditionOperator.GREATER_THAN:
            try:
                # Try numeric comparison
                num_value = float(value_str)
                num_condition = float(condition.value or "0")
                return num_value > num_condition
            except (ValueError, TypeError):
                # Fall back to string comparison
                return value_str > (condition.value or "")
        
        elif operator == ConditionOperator.LESS_THAN:
            try:
                # Try numeric comparison
                num_value = float(value_str)
                num_condition = float(condition.value or "0")
                return num_value < num_condition
            except (ValueError, TypeError):
                # Fall back to string comparison
                return value_str < (condition.value or "")
        
        elif operator == ConditionOperator.BETWEEN:
            try:
                # Try numeric comparison
                num_value = float(value_str)
                num_min = float(condition.valueMin or "0")
                num_max = float(condition.valueMax or "0")
                return num_min <= num_value <= num_max
            except (ValueError, TypeError):
                # Fall back to string comparison
                return (condition.valueMin or "") <= value_str <= (condition.valueMax or "")
        
        return False
    
    def evaluate_from_previous_result(
        self,
        previous_result: Dict[str, Any],
        conditions: List[Condition],
        field_name: str = "document_type"
    ) -> ConditionResult:
        """
        Evaluate conditions from previous workflow result.
        
        This is a convenience method for workflow execution.
        
        Args:
            previous_result: Result from previous workflow node
            conditions: List of conditions to evaluate
            field_name: Field name to extract from result (default: document_type)
            
        Returns:
            ConditionResult with matched condition index
        """
        # Try to extract value from common result structures
        value = None
        
        # Check for classification result
        if "document_type" in previous_result:
            value = previous_result["document_type"]
        elif "results" in previous_result and isinstance(previous_result["results"], list):
            # Classification result with results array
            if previous_result["results"]:
                first_result = previous_result["results"][0]
                if isinstance(first_result, dict) and "documentType" in first_result:
                    value = first_result["documentType"]
        elif "structured_data" in previous_result:
            # Extraction result
            structured_data = previous_result["structured_data"]
            if isinstance(structured_data, dict) and field_name in structured_data:
                value = structured_data[field_name]
        
        # If no value found, use the entire result
        if value is None:
            value = previous_result
        
        return self.evaluate(value, conditions, None)
