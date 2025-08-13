#!/usr/bin/env python3
"""
Test script for paper_checker evaluation functionality.

This script validates that the evaluation code correctly:
1. Handles compressed groundtruth files
2. Detects LaTeX citation and reference issues
3. Performs proper cleanup
"""

import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=cwd
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def create_test_workspace_with_errors():
    """Create a test workspace with LaTeX citation/reference errors"""
    temp_dir = tempfile.mkdtemp(prefix="paper_checker_test_")
    my_paper_dir = os.path.join(temp_dir, "my_paper")
    os.makedirs(my_paper_dir, exist_ok=True)
    
    # Create a test .tex file with citation errors
    tex_content = r"""
\documentclass{article}
\begin{document}
\title{Test Paper}
\author{Test Author}
\maketitle

\section{Introduction}
This is a test paper with citation errors.
We reference \cite{nonexistent_citation} which doesn't exist.
Also see \autoref{fig:wrong-label} for details.
The table is shown in \autoref{tab:incorrect-table}.

\section{Related Work}
Previous work \citep{missing_reference} has shown that...
See \S\ref{sec:wrong-section} for more details.

\end{document}
"""
    
    # Create a test .bib file
    bib_content = r"""
@article{correct_citation,
  title={A Correct Citation},
  author={Author, Test},
  journal={Test Journal},
  year={2023}
}

@inproceedings{another_correct,
  title={Another Correct Reference},
  author={Second, Author},
  booktitle={Test Conference},
  year={2024}
}
"""
    
    with open(os.path.join(my_paper_dir, "test.tex"), "w") as f:
        f.write(tex_content)
    
    with open(os.path.join(my_paper_dir, "references.bib"), "w") as f:
        f.write(bib_content)
    
    return temp_dir

def create_correct_test_workspace():
    """Create a test workspace with correct LaTeX citations/references"""
    temp_dir = tempfile.mkdtemp(prefix="paper_checker_correct_")
    my_paper_dir = os.path.join(temp_dir, "my_paper")
    os.makedirs(my_paper_dir, exist_ok=True)
    
    # Create a test .tex file with correct citations
    tex_content = r"""
\documentclass{article}
\begin{document}
\title{Test Paper}
\author{Test Author}
\maketitle

\section{Introduction}
\label{sec:intro}
This is a test paper with correct citations.
We reference \cite{correct_citation} which exists.
Also see \autoref{fig:correct-label} for details.
The table is shown in \autoref{tab:correct-table}.

\section{Related Work}
\label{sec:related}
Previous work \citep{another_correct} has shown that...
See \S\ref{sec:intro} for more details.

\end{document}
"""
    
    # Same .bib file as before
    bib_content = r"""
@article{correct_citation,
  title={A Correct Citation},
  author={Author, Test},
  journal={Test Journal},
  year={2023}
}

@inproceedings{another_correct,
  title={Another Correct Reference},
  author={Second, Author},
  booktitle={Test Conference},
  year={2024}
}
"""
    
    with open(os.path.join(my_paper_dir, "test.tex"), "w") as f:
        f.write(tex_content)
    
    with open(os.path.join(my_paper_dir, "references.bib"), "w") as f:
        f.write(bib_content)
    
    return temp_dir

def test_evaluation_functionality():
    """Test the core evaluation functionality"""
    print("🧪 Testing paper_checker evaluation functionality...\n")
    
    # Get project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    
    test_results = {
        "compression_handling": False,
        "error_detection": False,
        "correct_validation": False,
        "cleanup": False
    }
    
    # Test 1: Verify compressed groundtruth handling works
    print("📦 Test 1: Testing compressed groundtruth handling...")
    
    # Create agent workspace with errors
    agent_workspace = create_test_workspace_with_errors()
    
    try:
        # Run evaluation against actual groundtruth (should detect differences)
        gt_workspace = project_root / "tasks/finalpool/paper_checker/groundtruth_workspace"
        
        cmd = f"uv run python -m tasks.finalpool.paper_checker.evaluation.main --agent_workspace {agent_workspace} --groundtruth_workspace {gt_workspace}"
        returncode, stdout, stderr = run_command(cmd, cwd=project_root)
        
        if "✓ Extracted groundtruth files to:" in stdout and "✓ Cleaned up extracted files from:" in stdout:
            test_results["compression_handling"] = True
            print("  ✓ Compression handling works correctly")
        else:
            print("  ✗ Compression handling failed")
            print(f"  stdout: {stdout}")
            print(f"  stderr: {stderr}")
        
        # Check that groundtruth workspace only contains compressed file after cleanup
        gt_files = os.listdir(gt_workspace)
        if "files.tar.gz" in gt_files and "my_paper" not in gt_files:
            test_results["cleanup"] = True
            print("  ✓ Cleanup works correctly")
        else:
            print("  ✗ Cleanup failed - extracted files still present")
            print(f"  Files in groundtruth workspace: {gt_files}")
    
    finally:
        shutil.rmtree(agent_workspace, ignore_errors=True)
    
    # Test 2: Verify error detection
    print("\n🔍 Test 2: Testing LaTeX error detection...")
    
    # Create two different workspaces - one with errors, one correct
    agent_with_errors = create_test_workspace_with_errors()
    correct_workspace = create_correct_test_workspace()
    
    try:
        # Compress correct workspace as "groundtruth"
        gt_test_dir = tempfile.mkdtemp(prefix="gt_test_")
        shutil.copy2(
            os.path.join(correct_workspace, "my_paper", "test.tex"),
            os.path.join(gt_test_dir, "test.tex")
        )
        shutil.copy2(
            os.path.join(correct_workspace, "my_paper", "references.bib"),
            os.path.join(gt_test_dir, "references.bib")
        )
        
        # Create a mock groundtruth structure
        gt_workspace_test = tempfile.mkdtemp(prefix="gt_workspace_")
        gt_paper_dir = os.path.join(gt_workspace_test, "my_paper")
        os.makedirs(gt_paper_dir, exist_ok=True)
        
        # Copy correct files to groundtruth
        shutil.copy2(
            os.path.join(correct_workspace, "my_paper", "test.tex"),
            os.path.join(gt_paper_dir, "test.tex")
        )
        shutil.copy2(
            os.path.join(correct_workspace, "my_paper", "references.bib"),
            os.path.join(gt_paper_dir, "references.bib")
        )
        
        # Test comparison between error workspace and correct workspace
        cmd = f"uv run python -m tasks.finalpool.paper_checker.evaluation.main --agent_workspace {agent_with_errors} --groundtruth_workspace {gt_workspace_test}"
        returncode, stdout, stderr = run_command(cmd, cwd=project_root)
        
        if returncode != 0 and "DIFFERENCES FOUND" in stdout:
            test_results["error_detection"] = True
            print("  ✓ Error detection works correctly")
            print("  📋 Detected differences in LaTeX citations/references")
        else:
            print("  ✗ Error detection failed")
            print(f"  Return code: {returncode}")
            print(f"  stdout: {stdout}")
        
        # Test 3: Verify correct validation (same files should pass)
        print("\n✅ Test 3: Testing correct validation...")
        
        cmd = f"uv run python -m tasks.finalpool.paper_checker.evaluation.main --agent_workspace {correct_workspace} --groundtruth_workspace {gt_workspace_test}"
        returncode, stdout, stderr = run_command(cmd, cwd=project_root)
        
        if returncode == 0 and "✓ All files match perfectly!" in stdout:
            test_results["correct_validation"] = True
            print("  ✓ Correct validation works")
        else:
            print("  ✗ Correct validation failed")
            print(f"  Return code: {returncode}")
            print(f"  stdout: {stdout}")
    
    finally:
        shutil.rmtree(agent_with_errors, ignore_errors=True)
        shutil.rmtree(correct_workspace, ignore_errors=True)
        shutil.rmtree(gt_workspace_test, ignore_errors=True)
    
    return test_results

def analyze_evaluation_effectiveness():
    """Analyze whether the evaluation effectively detects LaTeX citation issues"""
    print("\n📊 Analysis: Evaluation Effectiveness for LaTeX Citation Issues")
    print("=" * 70)
    
    print("✅ STRENGTHS:")
    print("  • Line-by-line comparison ensures exact citation accuracy")
    print("  • Detects broken \\cite{}, \\autoref{}, \\ref{} commands")
    print("  • Catches missing or incorrect reference labels")
    print("  • Validates both .tex and .bib file consistency")
    print("  • Comprehensive file traversal (recursive directory search)")
    
    print("\n⚠️  LIMITATIONS:")
    print("  • No semantic validation of citation correctness")
    print("  • Cannot detect if citation exists in .bib but label is wrong")
    print("  • No LaTeX compilation check for undefined references")
    print("  • Very strict - sensitive to whitespace/formatting differences")
    print("  • Cannot detect logical issues (e.g., citing wrong paper)")
    
    print("\n🎯 TASK ALIGNMENT:")
    print("  The evaluation method is WELL-SUITED for the task because:")
    print("  • Task requires fixing broken citations → exact matching validates fixes")
    print("  • Ground truth provides correct citations → comparison ensures accuracy")
    print("  • Line-by-line comparison catches all textual citation errors")
    print("  • Supports both English and Chinese LaTeX documents")
    
    print("\n💡 EFFECTIVENESS RATING: 8.5/10")
    print("  High effectiveness for detecting citation/reference formatting issues.")
    print("  Could be enhanced with LaTeX compilation validation.")

def main():
    """Main test execution"""
    print("Paper Checker Evaluation Test Suite")
    print("=" * 50)
    
    # Run functionality tests
    results = test_evaluation_functionality()
    
    # Print test summary
    print("\n📋 TEST SUMMARY:")
    print("=" * 30)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests PASSED! Evaluation code is working correctly.")
    else:
        print("⚠️  Some tests FAILED. Please check the implementation.")
    
    # Analyze effectiveness
    analyze_evaluation_effectiveness()
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
