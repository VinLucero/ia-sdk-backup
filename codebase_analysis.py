#!/usr/bin/env python3
"""
Comprehensive codebase analysis for ia-sdk
Maps out the entire codebase structure, dependencies, and functionality
"""
import os
import ast
import sys
from datetime import datetime
import importlib
import inspect
from typing import Dict, List, Set, Tuple

class ModuleAnalysis:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        self.classes: List[str] = []
        self.functions: List[str] = []
        self.dependencies: Set[str] = set()
        self.doc_status = "Unknown"
        self.test_status = "Unknown"
        self.source_code = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "path": self.path,
            "classes": self.classes,
            "functions": self.functions,
            "dependencies": list(self.dependencies),
            "doc_status": self.doc_status,
            "test_status": self.test_status
        }

def analyze_file(file_path: str) -> ModuleAnalysis:
    """Analyze a single Python file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    analysis = ModuleAnalysis(module_name, file_path)
    analysis.source_code = content
    
    try:
        tree = ast.parse(content)
        
        # Analyze imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    analysis.dependencies.add(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    analysis.dependencies.add(node.module)
            
            # Find classes and functions
            if isinstance(node, ast.ClassDef):
                analysis.classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                analysis.functions.append(node.name)
        
        # Check documentation status
        module_doc = ast.get_docstring(tree)
        class_docs = [ast.get_docstring(node) for node in tree.body if isinstance(node, ast.ClassDef)]
        func_docs = [ast.get_docstring(node) for node in tree.body if isinstance(node, ast.FunctionDef)]
        
        total_items = len(analysis.classes) + len(analysis.functions) + 1  # +1 for module
        documented_items = (
            (1 if module_doc else 0) +
            sum(1 for doc in class_docs if doc) +
            sum(1 for doc in func_docs if doc)
        )
        
        doc_percentage = (documented_items / total_items) * 100 if total_items > 0 else 0
        analysis.doc_status = f"{doc_percentage:.1f}% documented"
        
    except Exception as e:
        print(f"Error analyzing {file_path}: {str(e)}")
        analysis.doc_status = "Error analyzing"
    
    return analysis

def analyze_codebase(src_dir: str = "src/ia/gaius") -> Dict[str, ModuleAnalysis]:
    """Analyze the entire codebase"""
    analyses = {}
    
    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                analysis = analyze_file(file_path)
                analyses[analysis.name] = analysis
    
    return analyses

def print_analysis_report(analyses: Dict[str, ModuleAnalysis]):
    """Print a comprehensive analysis report"""
    print("\n=== ia-sdk Codebase Analysis ===")
    print(f"Analysis Date: {datetime.now()}")
    print(f"Total Modules: {len(analyses)}")
    
    # Module Overview
    print("\n=== Module Overview ===")
    for name, analysis in sorted(analyses.items()):
        print(f"\n{name}:")
        print(f"  Path: {analysis.path}")
        print(f"  Classes: {', '.join(analysis.classes) or 'None'}")
        print(f"  Functions: {', '.join(analysis.functions) or 'None'}")
        print(f"  Dependencies: {', '.join(sorted(analysis.dependencies)) or 'None'}")
        print(f"  Documentation: {analysis.doc_status}")
    
    # Dependency Graph
    print("\n=== Dependency Graph ===")
    internal_deps = {}
    for name, analysis in analyses.items():
        internal_deps[name] = {
            dep for dep in analysis.dependencies 
            if any(dep.startswith(f"ia.gaius.{m}") for m in analyses.keys())
        }
    
    for module, deps in sorted(internal_deps.items()):
        if deps:
            print(f"{module} -> {', '.join(sorted(deps))}")
    
    # Documentation Status
    print("\n=== Documentation Status ===")
    doc_percentages = [
        float(analysis.doc_status.split('%')[0])
        for analysis in analyses.values()
        if '%' in analysis.doc_status
    ]
    if doc_percentages:
        avg_doc = sum(doc_percentages) / len(doc_percentages)
        print(f"Average documentation coverage: {avg_doc:.1f}%")
    
    # Recommendations
    print("\n=== Recommendations ===")
    for name, analysis in sorted(analyses.items()):
        if '%' in analysis.doc_status:
            doc_percent = float(analysis.doc_status.split('%')[0])
            if doc_percent < 50:
                print(f"- {name}: Needs documentation improvement ({analysis.doc_status})")

if __name__ == "__main__":
    print("Starting comprehensive codebase analysis...")
    analyses = analyze_codebase()
    print_analysis_report(analyses)
