# Condition Node

The Condition Node evaluates conditions against data from previous workflow nodes to determine routing paths in the workflow.

## Features

- Multiple condition operators: equals, not_equals, greater_than, less_than, contains, between
- Case-insensitive string comparison
- Numeric comparison support
- Multiple output paths based on condition matching
- Else path for unmatched conditions

## API Endpoint

### POST /condition/evaluate

Evaluates conditions against previous workflow result.

**Request Parameters:**
- `conditions` (string, required): JSON array of condition definitions
- `previous_result` (string, required): JSON string with previous node result
- `field_name` (string, optional): Field name to evaluate (default: "document_type")

**Condition Format:**
```json
[
  {
    "operator": "equals",
    "value": "invoice"
  },
  {
    "operator": "between",
    "valueMin": "100",
    "valueMax": "1000"
  }
]
```

**Response:**
```json
{
  "success": true,
  "matched_index": 0,
  "is_else": false
}
```

- `matched_index`: Index of the matched condition (0-based), or `null` for else path
- `is_else`: `true` if no condition matched (else path)

## Operators

### equals
Checks if value equals the condition value (case-insensitive).

```json
{
  "operator": "equals",
  "value": "invoice"
}
```

### not_equals
Checks if value does not equal the condition value (case-insensitive).

```json
{
  "operator": "not_equals",
  "value": "receipt"
}
```

### contains
Checks if value contains the condition value (case-insensitive).

```json
{
  "operator": "contains",
  "value": "tax"
}
```

### greater_than
Checks if value is greater than the condition value (numeric or string comparison).

```json
{
  "operator": "greater_than",
  "value": "100"
}
```

### less_than
Checks if value is less than the condition value (numeric or string comparison).

```json
{
  "operator": "less_than",
  "value": "100"
}
```

### between
Checks if value is between min and max values (inclusive, numeric or string comparison).

```json
{
  "operator": "between",
  "valueMin": "10",
  "valueMax": "100"
}
```

## Usage in Workflows

The condition node is typically used after classification or extraction nodes to route documents based on their type or extracted data.

### Example 1: Route by Document Type

```
Upload → Classify → Condition → [Extract Invoice | Extract Receipt | Other]
```

Conditions:
1. `equals "invoice"` → Route to Invoice extraction
2. `equals "receipt"` → Route to Receipt extraction
3. Else → Route to generic processing

### Example 2: Route by Amount

```
Upload → Extract → Condition → [High Value | Low Value]
```

Conditions:
1. `greater_than "1000"` → High value processing
2. Else → Standard processing

## Frontend Integration

The condition node in the frontend:
- Displays multiple output dots (one per condition + else)
- Shows condition count in node body
- Allows adding/removing conditions in settings panel
- Supports all operator types with appropriate UI

## Testing

Run tests with:
```bash
cd backend
python -m pytest tests/test_condition_evaluator.py -v
```

## Implementation Details

The `ConditionEvaluator` class:
- Evaluates conditions in order (first match wins)
- Returns matched condition index or None for else
- Supports extracting values from nested result structures
- Handles both classification and extraction result formats
- Performs case-insensitive string comparisons
- Attempts numeric comparison when possible, falls back to string comparison
