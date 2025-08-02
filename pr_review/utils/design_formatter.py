#!/usr/bin/env python3
"""
Design Analysis Formatter - Clean, minimalistic output formatting
"""

from typing import Dict, Any, List

def format_design_analysis(metrics: Dict[str, Any]) -> str:
    """Format design analysis in clean, condensed format"""
    if not metrics:
        return ""
    
    design_score = metrics.get('design_score', 'UNKNOWN')
    issues_found = metrics.get('design_issues_found', 0)
    issues = metrics.get('issues', [])
    
    if issues_found == 0:
        return f"Quality **{design_score}** • No issues detected"
    
    output_lines = [f"Quality **{design_score}** • {issues_found} issue{'s' if issues_found != 1 else ''} detected"]
    
    for issue in issues:
        principle = issue.get('principle', 'Unknown Principle')
        severity = issue.get('severity', 'UNKNOWN')
        description = issue.get('description', 'No description')
        suggestions = issue.get('suggestions', [])
        
        output_lines.append(f"\n**{principle}** ({severity})")
        output_lines.append(f"{description}")
        
        if suggestions:
            output_lines.append("Suggestions:")
            for suggestion in suggestions[:2]:
                output_lines.append(f"- {suggestion}")
    
    return '\n'.join(output_lines)

def format_metrics_summary(metrics: Dict[str, Any]) -> str:
    """Format all metrics in condensed lines"""
    lines_added = metrics.get('lines_added', 0)
    functions_added = metrics.get('functions_added', 0)
    complexity_added = metrics.get('cyclomatic_complexity_added', 0)
    risk_level = metrics.get('risk_level', 'UNKNOWN')
    
    fan_out = metrics.get('fan_out', 0)
    fan_in = metrics.get('fan_in', 0)
    coupling_factor = metrics.get('coupling_factor', 0.0)
    imports_added = metrics.get('imports_added', 0)
    exports_added = metrics.get('exports_added', 0)
    
    return f"""{lines_added} lines • {functions_added} functions • Complexity +{complexity_added} • Risk **{risk_level}**
Fan-Out {fan_out} • Fan-In {fan_in} • Coupling {coupling_factor:.2f} • Imports {imports_added} • Exports {exports_added}"""