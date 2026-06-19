"""Minimal YAML parser for OKF frontmatter."""

import re
from typing import Dict, List, Optional, Any


class SimpleYAMLParser:
    """Minimal YAML parser for OKF frontmatter."""

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        if not text.strip():
            return None

        result: Dict[str, Any] = {}
        lines = text.strip().split('\n')
        current_key: Optional[str] = None
        current_list: Optional[List[str]] = None

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                if current_list and current_key:
                    result[current_key] = current_list
                    current_key = None
                    current_list = None
                continue

            if stripped.startswith('- '):
                if current_key:
                    if current_list is None:
                        current_list = []
                    value = stripped[2:].strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    current_list.append(value)
                continue

            if ':' in line:
                if current_list and current_key:
                    result[current_key] = current_list
                    current_key = None
                    current_list = None

                colon_pos = line.find(':')
                key = line[:colon_pos].strip()
                value = line[colon_pos + 1:].strip()

                if not value:
                    current_key = key
                    current_list = None
                elif value.startswith('[') and value.endswith(']'):
                    items = value[1:-1].split(',')
                    result[key] = [item.strip().strip('"' + "'") for item in items if item.strip()]
                elif value.lower() in ('true', 'false'):
                    result[key] = value.lower() == 'true'
                elif value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                    result[key] = int(value)
                elif re.match(r'^-?\d+\.?\d*$', value):
                    result[key] = float(value)
                else:
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    result[key] = value

        if current_list and current_key:
            result[current_key] = current_list

        return result if result else None

    def dump(self, data: Dict[str, Any]) -> str:
        """Convert dict to YAML string."""
        lines = []
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            elif isinstance(value, bool):
                lines.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, (int, float)):
                lines.append(f"{key}: {value}")
            else:
                # Escape quotes in string values
                escaped = str(value).replace('"', '\\"')
                lines.append(f'{key}: "{escaped}"')
        return '\n'.join(lines)