#!/usr/bin/env python3
"""
NEXUS Schema Diff Analyzer

Analyzes git diffs for schema files and provides structured summaries
of what changed (added/removed models, fields, etc.)

Usage:
    python3 analyze_schema_diff.py [--range <commit_range>] [--file <filename>]

Examples:
    python3 analyze_schema_diff.py                    # Analyze unstaged changes
    python3 analyze_schema_diff.py --range HEAD~1..HEAD  # Analyze last commit
    python3 analyze_schema_diff.py --file schemas.py     # Analyze specific file
"""

import subprocess
import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import argparse

# Schema files to analyze by default
DEFAULT_SCHEMA_FILES = [
    "app/models/schemas.py",
    "app/models/agent_schemas.py"
]

class SchemaDiffAnalyzer:
    """Analyzes git diffs for schema files."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

    def get_diff(self, filepath: str, commit_range: Optional[str] = None) -> str:
        """Get git diff for a file."""
        cmd = ["git", "diff"]
        if commit_range:
            cmd.append(commit_range)
        cmd.append("--")
        cmd.append(filepath)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error getting diff for {filepath}: {e}", file=sys.stderr)
            return ""

    def analyze_diff(self, diff_content: str, filename: str) -> Dict[str, Any]:
        """Analyze diff content and extract structured information."""
        if not diff_content:
            return {"filename": filename, "has_changes": False}

        lines = diff_content.split('\n')

        # Extract added/removed class definitions
        added_classes = []
        removed_classes = []
        modified_classes = []

        # Track current class being analyzed
        current_class = None
        in_class_diff = False
        class_lines = []

        for i, line in enumerate(lines):
            # Look for class definitions in diff
            if line.startswith('+') and 'class ' in line and 'BaseModel' in line:
                class_name = self._extract_class_name(line[1:])  # Remove '+'
                if class_name:
                    added_classes.append(class_name)
            elif line.startswith('-') and 'class ' in line and 'BaseModel' in line:
                class_name = self._extract_class_name(line[1:])  # Remove '-'
                if class_name:
                    removed_classes.append(class_name)

            # Look for field changes
            if line.startswith('+') and (':' in line or '=' in line) and not line.startswith('+++'):
                # This might be a field addition
                pass
            elif line.startswith('-') and (':' in line or '=' in line) and not line.startswith('---'):
                # This might be a field removal
                pass

        # Simple regex-based analysis for field changes
        field_pattern = r'^[+-]\s*(\w+)\s*:'
        field_changes = []

        for line in lines:
            match = re.match(field_pattern, line)
            if match:
                field_name = match.group(1)
                change_type = 'added' if line.startswith('+') else 'removed'
                field_changes.append({
                    'field': field_name,
                    'type': change_type,
                    'line': line.strip()
                })

        # Look for model changes (more sophisticated)
        model_changes = self._analyze_model_changes(diff_content)

        return {
            "filename": filename,
            "has_changes": True,
            "added_classes": added_classes,
            "removed_classes": removed_classes,
            "field_changes": field_changes,
            "model_changes": model_changes,
            "raw_diff": diff_content[:1000] + "..." if len(diff_content) > 1000 else diff_content
        }

    def _extract_class_name(self, line: str) -> Optional[str]:
        """Extract class name from a line."""
        match = re.search(r'class\s+(\w+)\s*\(', line)
        return match.group(1) if match else None

    def _analyze_model_changes(self, diff_content: str) -> List[Dict[str, Any]]:
        """Analyze model changes more thoroughly."""
        lines = diff_content.split('\n')
        model_changes = []
        current_model = None
        current_changes = []

        for line in lines:
            # Start of a model definition
            if 'class ' in line and 'BaseModel' in line:
                if current_model and current_changes:
                    model_changes.append({
                        'model': current_model,
                        'changes': current_changes.copy()
                    })

                # Extract model name
                match = re.search(r'class\s+(\w+)\s*\(', line)
                if match:
                    current_model = match.group(1)
                    current_changes = []
                    change_type = 'added' if line.startswith('+') else 'removed' if line.startswith('-') else 'modified'
                    current_changes.append({
                        'type': 'model_' + change_type,
                        'detail': line.strip()
                    })

            # Field changes within a model
            elif current_model and (line.startswith('+') or line.startswith('-')):
                # Skip diff headers
                if line.startswith('+++') or line.startswith('---'):
                    continue

                # Check if this looks like a field
                if ':' in line or '=' in line:
                    # Clean up the line
                    clean_line = line[1:].strip()  # Remove +/- and whitespace

                    # Try to extract field name and type
                    field_match = re.match(r'(\w+)\s*:\s*([^=]+)(?:\s*=\s*(.+))?', clean_line)
                    if field_match:
                        field_name = field_match.group(1)
                        field_type = field_match.group(2).strip()
                        default_value = field_match.group(3) if field_match.group(3) else None

                        change_type = 'field_added' if line.startswith('+') else 'field_removed'

                        current_changes.append({
                            'type': change_type,
                            'field': field_name,
                            'field_type': field_type,
                            'default': default_value,
                            'line': line.strip()
                        })

        # Add the last model if we were tracking one
        if current_model and current_changes:
            model_changes.append({
                'model': current_model,
                'changes': current_changes.copy()
            })

        return model_changes

    def format_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format analysis results for display."""
        output = []

        filename = analysis['filename']
        has_changes = analysis['has_changes']

        output.append(f"📄 {filename}")
        output.append("=" * 60)

        if not has_changes:
            output.append("No changes detected")
            output.append("")
            return "\n".join(output)

        # Show class-level changes
        added_classes = analysis['added_classes']
        removed_classes = analysis['removed_classes']

        if added_classes:
            output.append("➕ ADDED MODELS:")
            for cls in added_classes:
                output.append(f"  • {cls}")
            output.append("")

        if removed_classes:
            output.append("➖ REMOVED MODELS:")
            for cls in removed_classes:
                output.append(f"  • {cls}")
            output.append("")

        # Show model changes
        model_changes = analysis['model_changes']
        if model_changes:
            output.append("📋 DETAILED MODEL CHANGES:")
            output.append("")

            for model_info in model_changes:
                model_name = model_info['model']
                changes = model_info['changes']

                output.append(f"  {model_name}:")

                # Group changes by type
                added_fields = []
                removed_fields = []
                other_changes = []

                for change in changes:
                    if change['type'] == 'field_added':
                        field_info = f"{change['field']}: {change['field_type']}"
                        if change['default']:
                            field_info += f" = {change['default']}"
                        added_fields.append(field_info)
                    elif change['type'] == 'field_removed':
                        field_info = f"{change['field']}: {change['field_type']}"
                        if 'default' in change and change['default']:
                            field_info += f" = {change['default']}"
                        removed_fields.append(field_info)
                    else:
                        other_changes.append(change['detail'])

                if added_fields:
                    output.append("    Added fields:")
                    for field in added_fields:
                        output.append(f"      + {field}")

                if removed_fields:
                    output.append("    Removed fields:")
                    for field in removed_fields:
                        output.append(f"      - {field}")

                if other_changes:
                    output.append("    Other changes:")
                    for change in other_changes:
                        output.append(f"      • {change}")

                output.append("")

        # Show simple field changes if no detailed model analysis
        elif analysis['field_changes']:
            output.append("🔧 FIELD CHANGES:")
            added_fields = [f for f in analysis['field_changes'] if f['type'] == 'added']
            removed_fields = [f for f in analysis['field_changes'] if f['type'] == 'removed']

            if added_fields:
                output.append("  Added:")
                for field in added_fields:
                    output.append(f"    + {field['line']}")

            if removed_fields:
                output.append("  Removed:")
                for field in removed_fields:
                    output.append(f"    - {field['line']}")

            output.append("")

        return "\n".join(output)

    def get_summary(self, analyses: List[Dict[str, Any]]) -> str:
        """Generate a summary of all analyses."""
        output = []

        total_changes = 0
        total_added_classes = 0
        total_removed_classes = 0
        total_added_fields = 0
        total_removed_fields = 0

        for analysis in analyses:
            if not analysis['has_changes']:
                continue

            total_changes += 1
            total_added_classes += len(analysis['added_classes'])
            total_removed_classes += len(analysis['removed_classes'])

            # Count field changes
            for model_info in analysis['model_changes']:
                for change in model_info['changes']:
                    if change['type'] == 'field_added':
                        total_added_fields += 1
                    elif change['type'] == 'field_removed':
                        total_removed_fields += 1

        output.append("📊 SCHEMA CHANGE SUMMARY")
        output.append("=" * 40)
        output.append(f"Files with changes: {total_changes}")
        output.append(f"Models added: {total_added_classes}")
        output.append(f"Models removed: {total_removed_classes}")
        output.append(f"Fields added: {total_added_fields}")
        output.append(f"Fields removed: {total_removed_fields}")
        output.append("")

        return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(
        description="Analyze git diffs for schema files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Analyze unstaged changes
  %(prog)s --range HEAD~1..HEAD  # Analyze last commit
  %(prog)s --file schemas.py     # Analyze specific file
  %(prog)s --summary             # Show summary only
        """
    )

    parser.add_argument(
        "--range", "-r",
        type=str,
        help="Git commit range (e.g., HEAD~1..HEAD, main..HEAD)"
    )

    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Analyze specific file instead of default schema files"
    )

    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Show summary only"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output including raw diffs"
    )

    args = parser.parse_args()

    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Get files to analyze
    if args.file:
        files_to_analyze = [args.file]
    else:
        files_to_analyze = DEFAULT_SCHEMA_FILES

    # Check if files exist
    existing_files = []
    for filepath in files_to_analyze:
        full_path = project_root / filepath
        if full_path.exists():
            existing_files.append(filepath)
        else:
            print(f"Warning: File not found: {filepath}", file=sys.stderr)

    if not existing_files:
        print("Error: No schema files found to analyze", file=sys.stderr)
        sys.exit(1)

    # Analyze each file
    analyzer = SchemaDiffAnalyzer(project_root)
    analyses = []

    print(f"Analyzing {len(existing_files)} schema file(s)...", file=sys.stderr)

    for filepath in existing_files:
        print(f"  Processing {filepath}...", file=sys.stderr)

        diff_content = analyzer.get_diff(filepath, args.range)
        analysis = analyzer.analyze_diff(diff_content, filepath)
        analyses.append(analysis)

    # Display results
    if args.summary:
        print(analyzer.get_summary(analyses))
    else:
        for analysis in analyses:
            print(analyzer.format_analysis(analysis))

        # Also show summary at the end
        print(analyzer.get_summary(analyses))

    # Show verbose output if requested
    if args.verbose:
        print("\n" + "="*60)
        print("VERBOSE OUTPUT (raw diffs):")
        print("="*60)

        for analysis in analyses:
            if analysis['has_changes']:
                print(f"\n{analysis['filename']}:")
                print("-" * 40)
                print(analysis['raw_diff'])

if __name__ == "__main__":
    main()