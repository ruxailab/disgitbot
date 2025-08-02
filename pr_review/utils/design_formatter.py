#!/usr/bin/env python3
"""
Design Analysis Formatter - Clean, minimalistic output formatting
"""

from typing import Dict, Any, List

def format_design_analysis(metrics: Dict[str, Any]) -> str:
    """
    Format design analysis results in a clean format
    
    Args:
        metrics: Full metrics dictionary containing design analysis
        
    Returns:
        Formatted string for display
    """
    if not metrics:
        return ""
    
    # Extract design analysis data
    design_score = metrics.get('design_score', 'UNKNOWN')
    issues_found = metrics.get('design_issues_found', 0)
    issues = metrics.get('issues', [])
    
    if issues_found == 0:
        return f"\n**Design Quality: {design_score}**\n   No design issues detected\n"
    
    # Build formatted output
    output_lines = []
    
    # Header with score
    output_lines.append(f"\n**Design Quality: {design_score}**")
    output_lines.append(f"   {issues_found} issue{'s' if issues_found != 1 else ''} detected\n")
    
    # Format each issue
    for i, issue in enumerate(issues, 1):
        severity = issue.get('severity', 'UNKNOWN')
        principle = issue.get('principle', 'Unknown Principle')
        description = issue.get('description', 'No description')
        suggestions = issue.get('suggestions', [])
        
        # Issue header with severity
        output_lines.append(f"**{principle}** ({severity})")
        output_lines.append(f"   {description}")
        
        # Suggestions (limit to 2 for brevity)
        if suggestions:
            output_lines.append("   Suggestions:")
            for suggestion in suggestions[:2]:
                output_lines.append(f"   - {suggestion}")
        
        # Add spacing between issues
        if i < len(issues):
            output_lines.append("")
    
    return '\n'.join(output_lines) + '\n'

def format_metrics_summary(metrics: Dict[str, Any]) -> str:
    """
    Format key metrics in a clean summary format
    
    Args:
        metrics: Full metrics dictionary
        
    Returns:
        Formatted metrics summary
    """
    lines_added = metrics.get('lines_added', 0)
    functions_added = metrics.get('functions_added', 0)
    complexity_added = metrics.get('cyclomatic_complexity_added', 0)
    risk_level = metrics.get('risk_level', 'UNKNOWN')
    
    # Fan-In/Fan-Out coupling metrics
    fan_out = metrics.get('fan_out', 0)
    fan_in = metrics.get('fan_in', 0)
    coupling_factor = metrics.get('coupling_factor', 0.0)
    imports_added = metrics.get('imports_added', 0)
    exports_added = metrics.get('exports_added', 0)
    
    output = f"""
**Code Metrics**
   {lines_added} lines added • {functions_added} functions • Complexity +{complexity_added}
   Risk: **{risk_level}**

**Coupling Analysis**
   Fan-Out: {fan_out} • Fan-In: {fan_in} • Coupling Factor: {coupling_factor:.2f}
   Imports: {imports_added} • Exports: {exports_added}
"""
    
    return output