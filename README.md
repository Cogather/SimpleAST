# SimpleAST - C++ Static Code Analyzer

A Python-based static analysis tool for C++ projects that works without compilation.

## Features

- **Entry Point Classification**: Distinguishes API functions (declared in .h) from internal functions (declared in .cpp)
- **Call Chain Tracing**: Traces function call chains from entry points
- **Function Signature Extraction**: Extracts complete function signatures and their definition locations
- **Data Structure Analysis**: Identifies data structure definitions and their usage across functions

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from cpp_analyzer import CppProjectAnalyzer

# Initialize analyzer with project root
analyzer = CppProjectAnalyzer(project_root="./your_cpp_project")

# Analyze a specific CPP file
result = analyzer.analyze_file("./your_cpp_project/src/main.cpp")

# Print formatted report
print(result.format_report())
```

## Limitations

- Does not expand complex macros
- Limited template instantiation support
- Cannot trace virtual function calls or function pointers accurately
- Requires manual configuration for custom include paths
