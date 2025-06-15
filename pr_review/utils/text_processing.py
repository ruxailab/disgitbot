import re
import logging
from typing import Dict, List, Any, Set

# Initialize logger
logger = logging.getLogger(__name__)

def preprocess_review_text(text: str) -> str:
    """
    Preprocess review text for embedding.
    
    Args:
        text: Raw review text
        
    Returns:
        Preprocessed text
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '[URL]', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_code_features(diff_text: str) -> Dict[str, Any]:
    """
    Extract features from a PR diff.
    
    Args:
        diff_text: Git diff text
        
    Returns:
        Dictionary of extracted features
    """
    if not diff_text:
        return {}
    
    features = {
        "file_types": set(),
        "file_paths": set(),
        "patterns": {
            "function_definitions": set(),
            "class_definitions": set(),
            "imports": set(),
            "sql_queries": set(),
            "api_endpoints": set()
        },
        "counts": {
            "files_changed": 0,
            "lines_added": 0,
            "lines_removed": 0
        }
    }
    
    # Extract file paths and types
    file_header_pattern = re.compile(r'diff --git a/(.*) b/(.*)')
    file_headers = file_header_pattern.findall(diff_text)
    
    for file_a, file_b in file_headers:
        features["counts"]["files_changed"] += 1
        features["file_paths"].add(file_b)
        
        # Extract file extension
        if '.' in file_b:
            extension = file_b.split('.')[-1].lower()
            features["file_types"].add(extension)
    
    # Count added and removed lines
    for line in diff_text.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            features["counts"]["lines_added"] += 1
            extract_code_patterns(line, features["patterns"])
        elif line.startswith('-') and not line.startswith('---'):
            features["counts"]["lines_removed"] += 1
    
    # Convert sets to lists for JSON serialization
    for key in features["file_types"]:
        features["file_types"] = list(features["file_types"])
    
    features["file_paths"] = list(features["file_paths"])
    
    for pattern_type in features["patterns"]:
        features["patterns"][pattern_type] = list(features["patterns"][pattern_type])
    
    return features

def extract_code_patterns(line: str, patterns: Dict[str, Set[str]]) -> None:
    """
    Extract code patterns from a line of code.
    
    Args:
        line: Line of code (without the leading + or -)
        patterns: Dictionary to store extracted patterns
    """
    # Remove the leading + or - if present
    if line.startswith('+') or line.startswith('-'):
        code_line = line[1:].strip()
    else:
        code_line = line.strip()
    
    # Function definitions
    function_patterns = [
        # Python
        r'def\s+([a-zA-Z0-9_]+)\s*\(',
        # JavaScript/TypeScript
        r'function\s+([a-zA-Z0-9_]+)\s*\(',
        # JavaScript/TypeScript arrow functions
        r'const\s+([a-zA-Z0-9_]+)\s*=\s*\([^)]*\)\s*=>',
        # Java/C#
        r'(public|private|protected|static|\s) +[\w\<\>\[\]]+\s+([a-zA-Z0-9_]+)\s*\([^\)]*\)\s*\{?'
    ]
    
    for pattern in function_patterns:
        matches = re.findall(pattern, code_line)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    # Some regex groups return tuples
                    function_name = match[-1]  # Last group is usually the function name
                else:
                    function_name = match
                patterns["function_definitions"].add(function_name)
    
    # Class definitions
    class_patterns = [
        # Python
        r'class\s+([a-zA-Z0-9_]+)',
        # JavaScript/TypeScript/Java/C#
        r'class\s+([a-zA-Z0-9_]+)'
    ]
    
    for pattern in class_patterns:
        matches = re.findall(pattern, code_line)
        if matches:
            for match in matches:
                patterns["class_definitions"].add(match)
    
    # Import statements
    import_patterns = [
        # Python
        r'import\s+([a-zA-Z0-9_\.]+)',
        r'from\s+([a-zA-Z0-9_\.]+)\s+import',
        # JavaScript/TypeScript
        r'import\s+\{?([^}]+)\}?\s+from\s+[\'"]([^\'"])[\'"]',
        r'require\([\'"]([^\'"]+)[\'"]\)',
        # Java
        r'import\s+([a-zA-Z0-9_\.]+);'
    ]
    
    for pattern in import_patterns:
        matches = re.findall(pattern, code_line)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    # Some regex groups return tuples
                    import_name = match[0]  # First group is usually the import name
                else:
                    import_name = match
                patterns["imports"].add(import_name)
    
    # SQL queries
    if 'SELECT' in code_line.upper() and ('FROM' in code_line.upper() or 'JOIN' in code_line.upper()):
        # Extract table names
        table_pattern = r'FROM\s+([a-zA-Z0-9_\.]+)|JOIN\s+([a-zA-Z0-9_\.]+)'
        matches = re.findall(table_pattern, code_line, re.IGNORECASE)
        if matches:
            for match in matches:
                if match[0]:  # FROM clause
                    patterns["sql_queries"].add(match[0])
                if match[1]:  # JOIN clause
                    patterns["sql_queries"].add(match[1])
    
    # API endpoints
    api_patterns = [
        # Express.js
        r'(app|router)\.(get|post|put|delete|patch)\s*\([\'"]([^\'"]+)[\'"]',
        # Flask/Django
        r'@(app|blueprint)\.route\([\'"]([^\'"]+)[\'"]',
        # Spring
        r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\s*\([\'"]([^\'"]+)[\'"]'
    ]
    
    for pattern in api_patterns:
        matches = re.findall(pattern, code_line)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    # Extract the endpoint path
                    endpoint = match[-1]  # Last group is usually the endpoint path
                    patterns["api_endpoints"].add(endpoint) 