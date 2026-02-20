#!/usr/bin/env python3
"""
GitHub Workflows Runner

Helper script to trigger all GitHub workflows for testing and development.
"""

import os
import subprocess
import sys
import yaml
from pathlib import Path
from typing import List, Dict, Any

class WorkflowRunner:
    """Manages GitHub workflow execution."""
    
    def __init__(self, workflows_dir: str = ".github/workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.workflows = self._discover_workflows()
    
    def _discover_workflows(self) -> List[Dict[str, Any]]:
        """Discover all workflow files in the workflows directory."""
        workflows = []
        
        if not self.workflows_dir.exists():
            print(f"Workflows directory {self.workflows_dir} not found")
            return workflows
        
        for workflow_file in self.workflows_dir.glob("*.yml"):
            try:
                with open(workflow_file, 'r') as f:
                    workflow_data = yaml.safe_load(f)
                    
                workflows.append({
                    'file': workflow_file.name,
                    'name': workflow_data.get('name', workflow_file.stem),
                    'has_workflow_dispatch': self._has_manual_trigger(workflow_data),
                    'path': str(workflow_file)
                })
            except Exception as e:
                print(f"Error reading {workflow_file}: {e}")
        
        return workflows
    
    def _has_manual_trigger(self, workflow_data: Dict[str, Any]) -> bool:
        """Check if workflow supports manual triggering."""
        on_config = workflow_data.get('on', {})
        
        # Handle both dict and list formats
        if isinstance(on_config, dict):
            return 'workflow_dispatch' in on_config
        elif isinstance(on_config, list):
            return 'workflow_dispatch' in on_config
        
        return False
    
    def list_workflows(self):
        """List all discovered workflows."""
        print("="*60)
        print("Available GitHub Workflows")
        print("="*60)
        
        if not self.workflows:
            print("No workflows found")
            return
        
        for i, workflow in enumerate(self.workflows, 1):
            manual_trigger = "" if workflow['has_workflow_dispatch'] else ""
            print(f"{i}. {workflow['name']}")
            print(f"   File: {workflow['file']}")
            print(f"   Manual trigger: {manual_trigger}")
            print()
    
    def run_workflow(self, workflow_name_or_index: str) -> bool:
        """Run a specific workflow by name or index."""
        workflow = self._find_workflow(workflow_name_or_index)
        
        if not workflow:
            print(f"Workflow '{workflow_name_or_index}' not found")
            return False
        
        if not workflow['has_workflow_dispatch']:
            print(f"Workflow '{workflow['name']}' does not support manual triggering")
            print("Add 'workflow_dispatch:' to the 'on:' section to enable manual runs")
            return False
        
        print(f"Triggering workflow: {workflow['name']}")
        
        try:
            result = subprocess.run([
                'gh', 'workflow', 'run', workflow['name']
            ], capture_output=True, text=True, check=True)
            
            print(f"Successfully triggered: {workflow['name']}")
            print(f"Output: {result.stdout}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to trigger workflow: {e}")
            print(f"Error: {e.stderr}")
            return False
        except FileNotFoundError:
            print("GitHub CLI (gh) not found. Please install it first:")
            print("https://cli.github.com/")
            return False
    
    def run_all_workflows(self) -> Dict[str, bool]:
        """Run all workflows that support manual triggering."""
        print("="*60)
        print("Running All Available Workflows")
        print("="*60)
        
        results = {}
        manual_workflows = [w for w in self.workflows if w['has_workflow_dispatch']]
        
        if not manual_workflows:
            print("No workflows support manual triggering")
            return results
        
        for workflow in manual_workflows:
            print(f"\nTriggering: {workflow['name']}")
            success = self.run_workflow(workflow['name'])
            results[workflow['name']] = success
        
        # Print summary
        print("\n" + "="*60)
        print("Workflow Execution Summary")
        print("="*60)
        
        for name, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            print(f"{status}: {name}")
        
        return results
    
    def _find_workflow(self, name_or_index: str):
        """Find workflow by name or index."""
        # Try by index first
        try:
            index = int(name_or_index) - 1
            if 0 <= index < len(self.workflows):
                return self.workflows[index]
        except ValueError:
            pass
        
        # Try by name
        for workflow in self.workflows:
            if workflow['name'].lower() == name_or_index.lower():
                return workflow
            if workflow['file'].lower() == name_or_index.lower():
                return workflow
        
        return None
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        print("Checking prerequisites...")
        
        # Check if we're in a git repository
        if not Path('.git').exists():
            print("Not in a git repository")
            return False
        
        # Check if GitHub CLI is installed
        try:
            subprocess.run(['gh', '--version'], capture_output=True, check=True)
            print("GitHub CLI is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("GitHub CLI not found. Install from: https://cli.github.com/")
            return False
        
        # Check if authenticated with GitHub
        try:
            result = subprocess.run(['gh', 'auth', 'status'], capture_output=True, text=True)
            if result.returncode == 0:
                print("GitHub CLI is authenticated")
            else:
                print("GitHub CLI not authenticated. Run: gh auth login")
                return False
        except Exception:
            print("Could not check GitHub CLI authentication")
            return False
        
        return True

def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub Workflows Runner")
    parser.add_argument('--list', '-l', action='store_true', help='List all workflows')
    parser.add_argument('--run', '-r', help='Run specific workflow by name or index')
    parser.add_argument('--all', '-a', action='store_true', help='Run all workflows')
    parser.add_argument('--check', '-c', action='store_true', help='Check prerequisites')
    
    args = parser.parse_args()
    
    runner = WorkflowRunner()
    
    if args.check:
        success = runner.check_prerequisites()
        sys.exit(0 if success else 1)
    
    if args.list:
        runner.list_workflows()
        return
    
    if args.run:
        success = runner.run_workflow(args.run)
        sys.exit(0 if success else 1)
    
    if args.all:
        results = runner.run_all_workflows()
        all_success = all(results.values())
        sys.exit(0 if all_success else 1)
    
    # Default: interactive mode
    runner.check_prerequisites()
    runner.list_workflows()
    
    while True:
        print("\nOptions:")
        print("1. Run specific workflow (enter number or name)")
        print("2. Run all workflows")
        print("3. Refresh workflow list")
        print("4. Exit")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '4' or choice.lower() == 'exit':
            break
        elif choice == '2':
            runner.run_all_workflows()
        elif choice == '3':
            runner = WorkflowRunner()  # Refresh
            runner.list_workflows()
        elif choice:
            runner.run_workflow(choice)

if __name__ == "__main__":
    main() 