#!/usr/bin/env python3
"""
Strict .env file format validator

Ensures that .env file matches .env.example format exactly:
- Same variable names in same order
- No extra/missing variables  
- No extra whitespace or formatting differences
- Only values on the right side of = can differ
- Configurable field requirements and warning messages
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# Field configuration - easily scalable for new fields
# 
# To add a new field:
# 1. Add it to .env.example
# 2. Add configuration here with:
#    - required: True/False (default: True)
#    - description: Human-readable description
#    - warning_if_empty: Custom warning message for optional fields
#
# Example:
# 'NEW_OPTIONAL_FIELD': {
#     'required': False,
#     'warning_if_empty': "NEW_OPTIONAL_FIELD is empty - this is fine for development but recommended for production.",
#     'description': 'Optional field for XYZ feature'
# }
FIELD_CONFIG = {
    'DISCORD_BOT_TOKEN': {
        'required': True,
        'description': 'Discord bot token for authentication'
    },
    'GITHUB_CLIENT_ID': {
        'required': True,
        'description': 'GitHub OAuth application client ID'
    },
    'GITHUB_CLIENT_SECRET': {
        'required': True,
        'description': 'GitHub OAuth application client secret'
    },
    'OAUTH_BASE_URL': {
        'required': True,
        'description': 'Base URL for OAuth redirects (your Cloud Run URL)'
    },
    'DISCORD_BOT_CLIENT_ID': {
        'required': True,
        'description': 'Discord application ID (client ID)'
    },
    'GITHUB_APP_ID': {
        'required': True,
        'description': 'GitHub App ID (required for SaaS mode)'
    },
    'GITHUB_APP_PRIVATE_KEY_B64': {
        'required': True,
        'description': 'Base64-encoded GitHub App private key PEM'
    },
    'GITHUB_APP_SLUG': {
        'required': True,
        'description': 'GitHub App slug (the /apps/<slug> part)'
    },
    'SECRET_KEY': {
        'required': True,
        'description': 'Flask session signing secret key (generate with: python3 -c "import secrets; print(secrets.token_hex(32))")'
    },
    'REPO_OWNER': {
        'required': False,
        'description': 'GitHub account/org that owns the disgitbot repo and has the GitHub App installed with Actions (read & write). Required for /sync to work. Defaults to ruxailab if not set.',
        'warning_if_empty': 'REPO_OWNER is empty — defaulting to ruxailab. Set this if your pipeline repo lives under a different org/user.'
    },
    'REPO_NAME': {
        'required': False,
        'description': 'Repository name hosting the pipeline workflow. Defaults to disgitbot.',
        'warning_if_empty': 'REPO_NAME is empty — defaulting to disgitbot. Set this if your repo has a different name.'
    },
    'WORKFLOW_REF': {
        'required': False,
        'description': 'Branch or tag to dispatch the pipeline workflow on. Defaults to main.',
        'warning_if_empty': 'WORKFLOW_REF is empty — defaulting to main. Set this if your active branch is not main (e.g. feature/saas-ready during testing).'
    }
}


def add_field_config(field_name: str, required: bool = True, description: str = '', warning_if_empty: str = '') -> None:
    """
    Helper function to add new field configuration programmatically.
    
    Args:
        field_name: The environment variable name
        required: Whether the field must have a value
        description: Human-readable description of the field
        warning_if_empty: Warning message to show if field is empty (for optional fields)
    """
    FIELD_CONFIG[field_name] = {
        'required': required,
        'description': description
    }
    if warning_if_empty:
        FIELD_CONFIG[field_name]['warning_if_empty'] = warning_if_empty


def parse_env_file(file_path: str) -> dict:
    """
    Parse .env file and return detailed analysis including variables and format issues.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    parsed_vars = []
    empty_lines = []
    comment_lines = []
    format_issues = []
    
    for line_num, line in enumerate(lines, 1):
        # Remove trailing newline but preserve other whitespace for format checking
        original_line = line
        line = line.rstrip('\n\r')
        
        # Check for trailing whitespace (except newlines)
        if line != line.rstrip():
            format_issues.append(f"Line {line_num}: trailing whitespace detected")
        
        # Detect empty lines (including whitespace-only lines)
        if not line.strip():
            empty_lines.append(line_num)
            continue
        
        # Detect comment lines    
        if line.strip().startswith('#'):
            comment_lines.append(line_num)
            continue
            
        # Check for valid KEY=VALUE format
        if '=' not in line:
            raise ValueError(f"Invalid format at line {line_num}: '{line}' (missing =)")
        
        # Split only on first = to handle values with = in them
        key, value = line.split('=', 1)
        
        # Check for whitespace around =
        if key != key.strip():
            format_issues.append(f"Line {line_num}: whitespace before = in '{line}'")
        if key.strip() != key:
            format_issues.append(f"Line {line_num}: whitespace in variable name '{key}'")
        if not key.strip():
            raise ValueError(f"Invalid format at line {line_num}: empty variable name in '{line}'")
        
        # Check for spaces after =
        if value != value.lstrip():
            format_issues.append(f"Line {line_num}: whitespace after = in '{line}'")
        
        # Check for quotes around values (common mistake)
        if value.startswith('"') and value.endswith('"'):
            format_issues.append(f"Line {line_num}: unnecessary quotes around value '{value}' - remove quotes unless they're part of the actual value")
        elif value.startswith("'") and value.endswith("'"):
            format_issues.append(f"Line {line_num}: unnecessary quotes around value '{value}' - remove quotes unless they're part of the actual value")
        
        # Check for mixed quote types
        if (value.startswith('"') and not value.endswith('"')) or (value.startswith("'") and not value.endswith("'")):
            format_issues.append(f"Line {line_num}: mismatched quotes in value '{value}'")
            
        parsed_vars.append((key.strip(), value))
    
    return {
        'variables': parsed_vars,
        'empty_lines': empty_lines,
        'comment_lines': comment_lines,
        'format_issues': format_issues,
        'total_lines': len(lines)
    }


def validate_env_strict(env_example_path: str, env_path: str) -> dict:
    """
    Perform strict line-by-line validation of .env file against .env.example.
    
    Returns:
        dict with validation results and detailed error information
    """
    result = {
        'valid': False,
        'errors': [],
        'warnings': [],
        'required_missing': [],
        'required_empty': [],
        'extra_vars': [],
        'order_mismatches': [],
        'format_errors': [],
        'line_mismatches': []
    }
    
    try:
        # Read both files line by line for strict comparison
        try:
            with open(env_example_path, 'r', encoding='utf-8') as f:
                example_lines = [line.rstrip('\r\n') for line in f.readlines()]
        except Exception as e:
            result['errors'].append(f"Failed to read .env.example: {e}")
            return result
            
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                env_lines = [line.rstrip('\r\n') for line in f.readlines()]
        except Exception as e:
            result['errors'].append(f"Failed to read .env: {e}")
            return result
        
        # 1. CHECK LINE COUNT
        # Extra lines beyond .env.example are always an error.
        # Fewer lines are allowed — optional vars at the end can be omitted;
        # FIELD_CONFIG handles missing optional fields as warnings below.
        if len(env_lines) > len(example_lines):
            extra_count = len(env_lines) - len(example_lines)
            result['format_errors'].append(
                f"Line count mismatch: expected at most {len(example_lines)} lines, found {len(env_lines)} lines"
            )
            result['format_errors'].append(
                f"Found {extra_count} extra line(s) at the end (lines {len(example_lines)+1}-{len(env_lines)})"
            )
        
        # 2. FOR EACH LINE: COMPARE VARIABLE NAMES (left of =) ONLY
        max_lines = min(len(example_lines), len(env_lines))  # Only compare existing lines
        for i in range(max_lines):
            line_num = i + 1
            expected_line = example_lines[i]
            actual_line = env_lines[i]
            
            # Handle empty lines and comments (should match exactly)
            if not expected_line.strip() or expected_line.strip().startswith('#'):
                if expected_line != actual_line:
                    result['line_mismatches'].append({
                        'line': line_num,
                        'expected': expected_line,
                        'actual': actual_line
                    })
                    result['format_errors'].append(
                        f"Line {line_num} format mismatch (empty/comment line must match exactly)"
                    )
                continue
            
            # Handle variable lines (VARIABLE=value)
            if '=' in expected_line and '=' in actual_line:
                expected_var = expected_line.split('=', 1)[0]  # Left side only
                actual_var = actual_line.split('=', 1)[0]      # Left side only
                
                if expected_var != actual_var:
                    result['line_mismatches'].append({
                        'line': line_num,
                        'expected': expected_var,
                        'actual': actual_var
                    })
                    result['format_errors'].append(
                        f"Line {line_num} variable name mismatch: expected '{expected_var}', found '{actual_var}'"
                    )
            elif '=' in expected_line or '=' in actual_line:
                # One has = and other doesn't - format error
                result['line_mismatches'].append({
                    'line': line_num,
                    'expected': expected_line,
                    'actual': actual_line
                })
                result['format_errors'].append(
                    f"Line {line_num} format error: inconsistent variable format"
                )
        
        # Parse .env file for additional validation and format checking
        try:
            env_data = parse_env_file(env_path)
            env_vars = env_data['variables']
            env_dict = {var[0]: var[1] for var in env_vars}
            
            # Add format issues to result
            if env_data.get('format_issues'):
                result['format_errors'].extend(env_data['format_issues'])
            
            # Only validate field requirements if structure matches (no extra lines, no key mismatches)
            if len(env_lines) <= len(example_lines) and len(result['line_mismatches']) == 0:
                # Check all configured fields based on their requirements
                for field_name, field_config in FIELD_CONFIG.items():
                    is_required = field_config.get('required', True)
                    warning_msg = field_config.get('warning_if_empty')
                    
                    if field_name not in env_dict:
                        if is_required:
                            result['required_missing'].append(field_name)
                        elif warning_msg:
                            result['warnings'].append(f"{field_name} is missing - {warning_msg}")
                    elif not env_dict[field_name].strip():
                        if is_required:
                            result['required_empty'].append(field_name)
                        elif warning_msg:
                            result['warnings'].append(warning_msg)
                        
        except Exception as e:
            result['errors'].append(f"Variable validation failed: {e}")
        
        # Validate only if structure matches AND all required fields have values
        result['valid'] = (
            len(result['errors']) == 0 and
            len(result['required_missing']) == 0 and
            len(result['required_empty']) == 0 and
            len(result['format_errors']) == 0 and
            len(result['line_mismatches']) == 0
        )
        
        # Add line counts to result for accurate printing using readlines
        with open(env_example_path, 'r') as f:
            result['example_line_count'] = len(f.readlines())
        with open(env_path, 'r') as f:
            result['env_line_count'] = len(f.readlines())
        
        return result
        
    except Exception as e:
        result['errors'].append(f"Validation failed: {e}")
        # Try to add line counts even if validation failed
        try:
            with open(env_example_path, 'r') as f:
                result['example_line_count'] = len(f.readlines())
            with open(env_path, 'r') as f:
                result['env_line_count'] = len(f.readlines())
        except:
            result['example_line_count'] = 0
            result['env_line_count'] = 0
        return result


def print_validation_results(result: dict, env_example_path: str, env_path: str, example_line_count: Optional[int] = None, env_line_count: Optional[int] = None):
    """Print detailed validation results with colors and formatting."""
    
    # Colors
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color
    
    if result['valid']:
        print(f"{GREEN}PASS: .env file validation passed!{NC}")
        print(f"{GREEN}PASS: Format matches .env.example exactly{NC}")
        print(f"{GREEN}PASS: All required fields have values{NC}")
        
        # Show warnings even on success
        if result['warnings']:
            print()
            print(f"{YELLOW}WARNINGS:{NC}")
            for warning in result['warnings']:
                print(f"  • {warning}")
        return
    
    print(f"{RED}FAIL: .env file validation failed!{NC}")
    print()
    
    # Print specific error categories
    if result['errors']:
        print(f"{RED}CRITICAL ERRORS:{NC}")
        for error in result['errors']:
            print(f"  • {error}")
        print()
    
    if result['format_errors']:
        print(f"{RED}FORMAT ERRORS:{NC}")
        for error in result['format_errors']:
            print(f"  • {error}")
        print()
    
    if result['line_mismatches']:
        print(f"{RED}LINE MISMATCHES:{NC}")
        for mismatch in result['line_mismatches'][:3]:  # Show first 3 mismatches
            line_num = mismatch['line']
            expected = mismatch['expected']
            actual = mismatch['actual']
            print(f"  • Line {line_num}: Expected '{expected}', Found '{actual}'")
        if len(result['line_mismatches']) > 3:
            print(f"  • ... and {len(result['line_mismatches']) - 3} more")
        print()
    
    if result['required_missing']:
        print(f"{RED}MISSING REQUIRED FIELDS:{NC}")
        for field in result['required_missing']:
            print(f"  • {field}")
        print()
    
    if result['required_empty']:
        print(f"{RED}EMPTY REQUIRED FIELDS:{NC}")
        for field in result['required_empty']:
            print(f"  • {field}")
        print()
    
    if result['warnings']:
        print(f"{YELLOW}WARNINGS:{NC}")
        for warning in result['warnings']:
            print(f"  • {warning}")
        print()

    print(f"{YELLOW}FIX: Copy .env.example and fill in your values ONLY{NC}")
    print(f"{YELLOW}RULES: No spaces around =, no quotes, no trailing whitespace{NC}")


def main():
    """Command line interface for env validation."""
    try:
        if len(sys.argv) != 3:
            print("Usage: python env_validator.py <.env.example> <.env>")
            sys.exit(1)
        
        env_example_path = sys.argv[1]
        env_path = sys.argv[2]
        
        # Validate that files exist
        if not os.path.exists(env_example_path):
            print(f"ERROR: .env.example file not found: {env_example_path}")
            sys.exit(1)
        
        if not os.path.exists(env_path):
            print(f"ERROR: .env file not found: {env_path}")
            sys.exit(1)
        
        # Perform validation
        result = validate_env_strict(env_example_path, env_path)
        
        # Print results
        print_validation_results(result, env_example_path, env_path, 
                                result.get('example_line_count'), result.get('env_line_count'))
        
        # Exit with appropriate code
        sys.exit(0 if result['valid'] else 1)
        
    except Exception as e:
        print(f"CRITICAL ERROR in validator:")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)  # Different exit code for crashes


if __name__ == "__main__":
    main() 
