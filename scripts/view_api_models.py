#!/usr/bin/env python3
"""
NEXUS API Model Viewer

Extracts and displays Pydantic models from NEXUS schema files.
Helps non-technical users understand API request/response structures.

Usage:
    python3 view_api_models.py [--markdown] [--simple] [--file <filename>]

Examples:
    python3 view_api_models.py                    # Show all models in simple text
    python3 view_api_models.py --markdown         # Show all models in markdown format
    python3 view_api_models.py --simple           # Simple summary only
    python3 view_api_models.py --file schemas.py  # Show models from specific file
"""

import ast
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse


class ModelExtractor:
    """Extracts Pydantic models from Python files using AST parsing."""

    def __init__(self):
        self.models = []

    def extract_from_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Extract all BaseModel classes from a Python file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {filepath}")
            return []
        except Exception as e:
            print(f"Error reading file {filepath}: {e}")
            return []

        return self.extract_from_source(content, filepath)

    def extract_from_source(self, source: str, filename: str = "<unknown>") -> List[Dict[str, Any]]:
        """Extract models from Python source code."""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            print(f"Syntax error in {filename}: {e}")
            return []

        models = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                model_info = self._extract_class_info(node, source)
                if model_info:
                    model_info['filename'] = filename
                    models.append(model_info)

        return models

    def _extract_class_info(self, class_node: ast.ClassDef, source: str) -> Optional[Dict[str, Any]]:
        """Extract information about a class if it's a BaseModel."""
        # Check if class inherits from BaseModel
        is_basemodel = False
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseModel':
                is_basemodel = True
                break
            elif isinstance(base, ast.Attribute) and base.attr == 'BaseModel':
                is_basemodel = True
                break

        if not is_basemodel:
            return None

        # Extract docstring
        docstring = ast.get_docstring(class_node)

        # Extract fields
        fields = []
        for item in class_node.body:
            if isinstance(item, ast.AnnAssign):
                field_info = self._extract_field_info(item, source)
                if field_info:
                    fields.append(field_info)
            elif isinstance(item, ast.Assign):
                # Handle assignments like: cached: bool = False
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_info = self._extract_assignment_field_info(target.id, item, source)
                        if field_info:
                            fields.append(field_info)

        return {
            'name': class_node.name,
            'docstring': docstring or "No documentation",
            'fields': fields,
            'line_number': class_node.lineno
        }

    def _extract_field_info(self, node: ast.AnnAssign, source: str) -> Optional[Dict[str, Any]]:
        """Extract field information from an annotated assignment."""
        if not isinstance(node.target, ast.Name):
            return None

        field_name = node.target.id

        # Extract type annotation
        type_str = ast.unparse(node.annotation) if hasattr(ast, 'unparse') else self._extract_type_string(node.annotation, source)

        # Check if field has a default value
        has_default = node.value is not None
        default_value = None
        is_optional = False

        if has_default:
            default_value = ast.unparse(node.value) if hasattr(ast, 'unparse') else self._extract_value_string(node.value, source)

        # Check if type is Optional (contains "Optional[" or ends with "= None")
        if "Optional[" in type_str or (has_default and default_value == "None"):
            is_optional = True

        # Check for Field() usage
        field_args = {}
        if has_default and isinstance(node.value, ast.Call):
            # Check if it's a Field() call
            if isinstance(node.value.func, ast.Name) and node.value.func.id == 'Field':
                field_args = self._extract_field_arguments(node.value, source)

        return {
            'name': field_name,
            'type': type_str,
            'has_default': has_default,
            'default_value': default_value,
            'is_optional': is_optional,
            'field_args': field_args
        }

    def _extract_assignment_field_info(self, field_name: str, node: ast.Assign, source: str) -> Optional[Dict[str, Any]]:
        """Extract field information from a regular assignment."""
        # This is a simplified version for assignments without type annotations
        has_default = True
        default_value = ast.unparse(node.value) if hasattr(ast, 'unparse') else self._extract_value_string(node.value, source)

        return {
            'name': field_name,
            'type': 'Any',  # Unknown type for unannotated assignments
            'has_default': has_default,
            'default_value': default_value,
            'is_optional': True,  # Assume optional since it has a default
            'field_args': {}
        }

    def _extract_field_arguments(self, call_node: ast.Call, source: str) -> Dict[str, Any]:
        """Extract arguments from a Field() call."""
        args = {}

        # Extract positional arguments
        for i, arg in enumerate(call_node.args):
            if i == 0:
                args['default'] = ast.unparse(arg) if hasattr(ast, 'unparse') else self._extract_value_string(arg, source)

        # Extract keyword arguments
        for kw in call_node.keywords:
            arg_name = kw.arg
            arg_value = ast.unparse(kw.value) if hasattr(ast, 'unparse') else self._extract_value_string(kw.value, source)
            args[arg_name] = arg_value

        return args

    def _extract_type_string(self, node: ast.AST, source: str) -> str:
        """Extract type string from AST node (fallback for Python < 3.9)."""
        lines = source.split('\n')
        if hasattr(node, 'lineno') and hasattr(node, 'col_offset'):
            line = lines[node.lineno - 1]
            # This is a simplified extraction - for production use ast.unparse
            return line[node.col_offset:].strip()
        return str(node)

    def _extract_value_string(self, node: ast.AST, source: str) -> str:
        """Extract value string from AST node (fallback for Python < 3.9)."""
        lines = source.split('\n')
        if hasattr(node, 'lineno') and hasattr(node, 'col_offset'):
            line = lines[node.lineno - 1]
            return line[node.col_offset:].strip()
        return str(node)


class ModelFormatter:
    """Formats extracted models for display."""

    @staticmethod
    def format_simple(models: List[Dict[str, Any]]) -> str:
        """Format models in simple text format."""
        output = []
        output.append("=" * 80)
        output.append("NEXUS API MODELS")
        output.append("=" * 80)
        output.append("")

        for model in models:
            output.append(f"MODEL: {model['name']}")
            output.append(f"File: {model['filename']} (line {model['line_number']})")
            output.append(f"Description: {model['docstring']}")
            output.append("Fields:")

            for field in model['fields']:
                optional_marker = " (optional)" if field['is_optional'] else " (required)"
                default_marker = f" [default: {field['default_value']}]" if field['has_default'] else ""
                output.append(f"  • {field['name']}: {field['type']}{optional_marker}{default_marker}")

                # Show Field() arguments if present
                if field['field_args']:
                    args_str = ", ".join(f"{k}={v}" for k, v in field['field_args'].items())
                    output.append(f"    Field arguments: {args_str}")

            output.append("")

        output.append(f"Total models found: {len(models)}")
        return "\n".join(output)

    @staticmethod
    def format_markdown(models: List[Dict[str, Any]]) -> str:
        """Format models in markdown format."""
        output = []
        output.append("# NEXUS API Models")
        output.append("")
        output.append(f"*Total models: {len(models)}*")
        output.append("")

        for model in models:
            output.append(f"## {model['name']}")
            output.append("")
            output.append(f"**File**: `{model['filename']}` (line {model['line_number']})")
            output.append("")
            output.append(f"**Description**: {model['docstring']}")
            output.append("")
            output.append("### Fields")
            output.append("")
            output.append("| Field | Type | Required | Default | Description |")
            output.append("|-------|------|----------|---------|-------------|")

            for field in model['fields']:
                required = "No" if field['is_optional'] else "Yes"
                default = field['default_value'] if field['has_default'] else "—"

                # Create description from Field arguments
                description_parts = []
                if field['field_args']:
                    for k, v in field['field_args'].items():
                        if k not in ['default', 'default_factory']:
                            description_parts.append(f"{k}={v}")

                description = "; ".join(description_parts) if description_parts else "—"

                output.append(f"| `{field['name']}` | `{field['type']}` | {required} | `{default}` | {description} |")

            output.append("")

        return "\n".join(output)

    @staticmethod
    def format_summary(models: List[Dict[str, Any]]) -> str:
        """Format a simple summary of models."""
        output = []
        output.append("NEXUS API Models Summary")
        output.append("=" * 40)
        output.append("")

        # Group by filename
        by_file = {}
        for model in models:
            filename = model['filename']
            if filename not in by_file:
                by_file[filename] = []
            by_file[filename].append(model)

        for filename, file_models in by_file.items():
            output.append(f"File: {filename}")
            output.append(f"  Models: {len(file_models)}")
            for model in file_models:
                field_count = len(model['fields'])
                output.append(f"    • {model['name']}: {field_count} fields - {model['docstring'][:60]}...")
            output.append("")

        total_fields = sum(len(model['fields']) for model in models)
        output.append(f"Total: {len(models)} models, {total_fields} fields")
        return "\n".join(output)


def get_schema_files() -> List[str]:
    """Get the default schema files to parse."""
    nexus_dir = Path(__file__).parent.parent
    schema_files = [
        str(nexus_dir / "app" / "models" / "schemas.py"),
        str(nexus_dir / "app" / "models" / "agent_schemas.py"),
    ]

    # Check which files exist
    existing_files = [f for f in schema_files if os.path.exists(f)]

    if not existing_files:
        print("Error: No schema files found. Looking for:")
        for f in schema_files:
            print(f"  - {f}")
        sys.exit(1)

    return existing_files


def main():
    parser = argparse.ArgumentParser(
        description="Extract and display Pydantic models from NEXUS schema files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Show all models in simple text format
  %(prog)s --markdown         Show all models in markdown format
  %(prog)s --simple           Show simple summary only
  %(prog)s --file schemas.py  Show models from specific file
        """
    )

    parser.add_argument(
        "--markdown", "-m",
        action="store_true",
        help="Output in markdown format"
    )

    parser.add_argument(
        "--simple", "-s",
        action="store_true",
        help="Output simple summary only"
    )

    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Parse specific file instead of default schema files"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Write output to file instead of stdout"
    )

    args = parser.parse_args()

    # Get files to parse
    if args.file:
        files_to_parse = [args.file]
    else:
        files_to_parse = get_schema_files()

    # Extract models
    extractor = ModelExtractor()
    all_models = []

    print(f"Parsing {len(files_to_parse)} file(s)...", file=sys.stderr)

    for filepath in files_to_parse:
        print(f"  Reading {os.path.basename(filepath)}...", file=sys.stderr)
        models = extractor.extract_from_file(filepath)
        all_models.extend(models)
        print(f"    Found {len(models)} models", file=sys.stderr)

    if not all_models:
        print("No Pydantic models found!", file=sys.stderr)
        sys.exit(1)

    # Format output
    if args.simple:
        output = ModelFormatter.format_summary(all_models)
    elif args.markdown:
        output = ModelFormatter.format_markdown(all_models)
    else:
        output = ModelFormatter.format_simple(all_models)

    # Write output
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Output written to {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing to {args.output}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)


if __name__ == "__main__":
    main()