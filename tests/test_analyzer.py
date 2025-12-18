"""
Test script for the C++ analyzer.
"""
import sys
import io
from cpp_analyzer import CppProjectAnalyzer

# Set output encoding to UTF-8 for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_analyzer():
    print("=" * 80)
    print("Testing SimpleAST C++ Analyzer")
    print("=" * 80)

    # Initialize analyzer with example project
    project_root = "./example_project"
    target_file = "src/main.cpp"

    try:
        # Create analyzer
        analyzer = CppProjectAnalyzer(project_root)

        # Analyze the main.cpp file
        result = analyzer.analyze_file(target_file)

        # Print the report
        print("\n" + result.format_report())

        # Save JSON output
        with open("test_output.json", "w") as f:
            f.write(result.to_json())

        print("\n\nJSON output saved to: test_output.json")
        print("\nTest completed successfully!")

    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_analyzer()
