# NEXUS API Model Viewer

This tool extracts and displays Pydantic models from NEXUS schema files. It helps non-technical users understand API request/response structures before approving changes.

## Quick Start

```bash
# Show all models in simple text format
./scripts/view_models.sh

# Show simple summary
./scripts/view_models.sh simple

# Show detailed markdown format
./scripts/view_models.sh markdown

# Show help
./scripts/view_models.sh help
```

## Detailed Usage

### Python Script (`view_api_models.py`)

The main Python script provides more options:

```bash
# Show all models in simple text format (default)
python3 scripts/view_api_models.py

# Show markdown format
python3 scripts/view_api_models.py --markdown

# Show simple summary
python3 scripts/view_api_models.py --simple

# Parse specific file
python3 scripts/view_api_models.py --file app/models/schemas.py

# Write output to file
python3 scripts/view_api_models.py --markdown --output models.md
```

### Bash Wrapper (`view_models.sh`)

Simplified wrapper for common use cases:

```bash
./scripts/view_models.sh          # Text format (default)
./scripts/view_models.sh simple   # Simple summary
./scripts/view_models.sh markdown # Markdown format
./scripts/view_models.sh help     # Show help
```

## What It Shows

For each Pydantic model, the tool displays:

1. **Model Name** - The class name
2. **File Location** - Which file contains the model
3. **Description** - The docstring/documentation
4. **Fields** - All fields with:
   - Field name
   - Type (e.g., `str`, `Optional[int]`, `List[dict]`)
   - Required/Optional status
   - Default value (if any)
   - Field constraints (e.g., `min_length=1`, `gt=0`)

## Example Output

### Simple Summary Format
```
NEXUS API Models Summary
========================================

File: /home/philip/nexus/app/models/schemas.py
  Models: 25
    • ChatRequest: 2 fields - Request body for chat endpoint....
    • ChatResponse: 6 fields - Response from chat endpoint....
    • ExpenseCreate: 5 fields - Create a new expense....
    ...

Total: 47 models, 354 fields
```

### Text Format (Detailed)
```
MODEL: ChatRequest
File: /home/philip/nexus/app/models/schemas.py (line 15)
Description: Request body for chat endpoint.
Fields:
  • message: str (required) [default: Field(..., min_length=1, max_length=10000)]
    Field arguments: default=..., min_length=1, max_length=10000
  • model: Optional[str] (optional) [default: None]
```

### Markdown Format
```markdown
## ChatRequest

**File**: `/home/philip/nexus/app/models/schemas.py` (line 15)

**Description**: Request body for chat endpoint.

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `message` | `str` | Yes | `Field(..., min_length=1, max_length=10000)` | min_length=1; max_length=10000 |
| `model` | `Optional[str]` | No | `None` | — |
```

## Files Parsed

By default, the tool parses:
1. `app/models/schemas.py` - Core API models (chat, finance, health, swarm)
2. `app/models/agent_schemas.py` - Agent framework models

You can specify other files with the `--file` option.

## Use Cases

1. **Understanding API Changes**: Before approving changes in Claude Code, view what models are affected
2. **Documentation**: Generate markdown documentation of all API models
3. **Learning**: Understand the structure of NEXUS API requests and responses
4. **Debugging**: Check field types and constraints when API calls fail

## Technical Details

The script uses Python's `ast` module to parse Python files and extract:
- Classes that inherit from `BaseModel`
- Class docstrings
- Field annotations and default values
- `Field()` constraints and validations

## Requirements

- Python 3.8+ (comes with NEXUS)
- No additional dependencies beyond standard library

## Integration with Claude Code

When reviewing API changes in Claude Code:

1. Run `./scripts/view_models.sh simple` to see what models exist
2. Review the changes Claude proposes
3. Run `./scripts/view_models.sh` to see detailed field information
4. Use `./scripts/view_models.sh markdown > models.md` to save documentation

This helps non-technical users understand API changes without reading Python code directly.