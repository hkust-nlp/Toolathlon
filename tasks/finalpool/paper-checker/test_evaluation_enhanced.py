#!/usr/bin/env python3
"""
Enhanced test script for paper-checker evaluation logic with normalize_str function.
Tests various scenarios including space and punctuation differences.
"""

import os
import sys
import tempfile
import shutil
import tarfile
import unittest
import importlib.util

# Get the absolute path to the project root
current_file = os.path.abspath(__file__)
paper_checker_dir = os.path.dirname(current_file)  # paper-checker directory
finalpool_dir = os.path.dirname(paper_checker_dir)  # finalpool directory
tasks_dir = os.path.dirname(finalpool_dir)  # tasks directory
project_root = os.path.dirname(tasks_dir)  # project root

# Add project root to path
sys.path.insert(0, project_root)

# Import normalize_str function
from utils.general.helper import normalize_str

# Import the evaluation functions directly
eval_main_path = os.path.join(paper_checker_dir, 'evaluation', 'main.py')
spec = importlib.util.spec_from_file_location("evaluation_main", eval_main_path)
evaluation_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation_main)

# Use the imported functions
compare_files = evaluation_main.compare_files
extract_groundtruth_files = evaluation_main.extract_groundtruth_files


class TestPaperCheckerEvaluation(unittest.TestCase):
    
    def setUp(self):
        """Set up test directories and files"""
        self.test_dir = tempfile.mkdtemp()
        self.agent_workspace = os.path.join(self.test_dir, "agent")
        self.groundtruth_workspace = os.path.join(self.test_dir, "groundtruth")
        
        # Create directory structure
        os.makedirs(os.path.join(self.agent_workspace, "my_paper"))
        os.makedirs(os.path.join(self.groundtruth_workspace, "my_paper"))
    
    def tearDown(self):
        """Clean up test directories"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def create_test_files(self, agent_content: str, groundtruth_content: str, filename: str = "test.tex"):
        """Helper to create test files with given content"""
        agent_file = os.path.join(self.agent_workspace, "my_paper", filename)
        gt_file = os.path.join(self.groundtruth_workspace, "my_paper", filename)
        
        with open(agent_file, 'w', encoding='utf-8') as f:
            f.write(agent_content)
        with open(gt_file, 'w', encoding='utf-8') as f:
            f.write(groundtruth_content)
    
    def test_exact_match(self):
        """Test that identical files pass evaluation"""
        content = "\\documentclass{article}\n\\begin{document}\nHello World\n\\end{document}\n"
        self.create_test_files(content, content)
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertTrue(result, f"Exact match should pass: {message}")
        self.assertEqual(message, "All files match")
    
    def test_space_differences_should_pass(self):
        """Test that files with only space differences should pass with normalize_str"""
        agent_content = "\\documentclass{article}\n\\begin{document}\nHello  World\n\\end{document}\n"
        gt_content = "\\documentclass{article}\n\\begin{document}\nHello World\n\\end{document}\n"
        
        self.create_test_files(agent_content, gt_content)
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertTrue(result, f"Space differences should pass with normalize_str: {message}")
    
    def test_punctuation_differences_should_pass(self):
        """Test that files with only punctuation differences should pass"""
        agent_content = "\\section{Introduction}\nThis is a test.\n"
        gt_content = "\\section{Introduction}\nThis is a test!\n"
        
        self.create_test_files(agent_content, gt_content)
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertTrue(result, f"Punctuation differences should pass: {message}")
    
    def test_mixed_whitespace_and_punctuation(self):
        """Test files with mixed whitespace and punctuation differences"""
        agent_content = "\\title{  My Paper  }\n\\author{John Doe,  Jane Smith}\n"
        gt_content = "\\title{My Paper}\n\\author{John Doe; Jane Smith}\n"
        
        self.create_test_files(agent_content, gt_content)
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertTrue(result, f"Mixed whitespace/punctuation should pass: {message}")
    
    def test_content_differences_should_fail(self):
        """Test that actual content differences should still fail"""
        agent_content = "\\section{Introduction}\nThis is the wrong content.\n"
        gt_content = "\\section{Introduction}\nThis is the correct content.\n"
        
        self.create_test_files(agent_content, gt_content)
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertFalse(result, "Content differences should fail evaluation")
        self.assertIn("Found differences", message)
    
    def test_case_insensitive_comparison(self):
        """Test that case differences are normalized"""
        agent_content = "\\SECTION{INTRODUCTION}\nHELLO WORLD\n"
        gt_content = "\\section{introduction}\nhello world\n"
        
        self.create_test_files(agent_content, gt_content)
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertTrue(result, f"Case differences should pass: {message}")
    
    def test_empty_lines_handling(self):
        """Test handling of empty lines and whitespace-only lines"""
        agent_content = "\\section{Test}\n\n  \n\\begin{document}\n"
        gt_content = "\\section{Test}\n\n\n\\begin{document}\n"
        
        self.create_test_files(agent_content, gt_content)
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertTrue(result, f"Empty line differences should pass: {message}")
    
    def test_multiple_files(self):
        """Test evaluation with multiple .tex and .bib files"""
        # Create main.tex files
        self.create_test_files(
            "\\documentclass{article}\n\\input{section1}\n",
            "\\documentclass{article}\n\\input{section1}\n",
            "main.tex"
        )
        
        # Create section1.tex files with space differences
        self.create_test_files(
            "\\section{Introduction}\nContent  here\n",
            "\\section{Introduction}\nContent here\n",
            "section1.tex"
        )
        
        # Create bib files with punctuation differences
        self.create_test_files(
            "@article{test2023,\n  title={Test Paper},\n  author={John Doe}\n}\n",
            "@article{test2023,\n  title={Test Paper};\n  author={John Doe}.\n}\n",
            "refs.bib"
        )
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertTrue(result, f"Multiple files with minor differences should pass: {message}")
    
    def test_missing_files(self):
        """Test behavior when agent is missing files"""
        # Only create groundtruth file
        gt_file = os.path.join(self.groundtruth_workspace, "my_paper", "missing.tex")
        with open(gt_file, 'w', encoding='utf-8') as f:
            f.write("\\section{Missing}\n")
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertFalse(result, "Missing files should fail evaluation")
        self.assertIn("Missing files", message)
    
    def test_extra_files_ignored(self):
        """Test that extra files in agent workspace are ignored"""
        # Create matching file
        self.create_test_files(
            "\\section{Main}\nContent\n",
            "\\section{Main}\nContent\n",
            "main.tex"
        )
        
        # Create extra file in agent workspace only
        extra_file = os.path.join(self.agent_workspace, "my_paper", "extra.tex")
        with open(extra_file, 'w', encoding='utf-8') as f:
            f.write("\\section{Extra}\n")
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertTrue(result, f"Extra files should be ignored: {message}")
    
    def test_normalize_str_function_directly(self):
        """Test the normalize_str function directly"""
        test_cases = [
            ("Hello World", "hello world", True),
            ("Hello,   World!", "Hello World", True),
            ("Test-Case_Example", "testcase_example", True),  # underscores are kept in \w
            ("Different Content", "other content", False),
            ("  Whitespace  ", "whitespace", True),
            ("Punctuation!!!", "punctuation", True),
            ("Mixed123Numbers", "mixed123numbers", True),
        ]
        
        for input1, input2, should_match in test_cases:
            norm1 = normalize_str(input1)
            norm2 = normalize_str(input2)
            actual_match = norm1 == norm2
            
            print(f"Testing: '{input1}' -> '{norm1}' vs '{input2}' -> '{norm2}'")
            
            self.assertEqual(
                actual_match, should_match,
                f"normalize_str('{input1}')='{norm1}' vs normalize_str('{input2}')='{norm2}' "
                f"should {'match' if should_match else 'not match'}"
            )
    
    def test_latex_specific_cases(self):
        """Test LaTeX-specific formatting scenarios"""
        # LaTeX commands with different spacing
        agent_content = "\\usepackage{  amsmath  }\n\\begin{equation}\n  E = mc^2\n\\end{equation}\n"
        gt_content = "\\usepackage{amsmath}\n\\begin{equation}\nE=mc^2\n\\end{equation}\n"
        
        self.create_test_files(agent_content, gt_content)
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertTrue(result, f"LaTeX formatting differences should pass: {message}")
    
    def test_bibliography_formatting(self):
        """Test bibliography entry formatting differences"""
        agent_content = """@article{smith2023,
  title = {A Great Paper},
  author = {John Smith and Jane Doe},
  year = {2023}
}"""
        
        gt_content = """@article{smith2023,
  title={A Great Paper},
  author={John Smith and Jane Doe},
  year={2023}
}"""
        
        self.create_test_files(agent_content, gt_content, "refs.bib")
        
        result, message = compare_files(self.agent_workspace, self.groundtruth_workspace)
        self.assertTrue(result, f"Bibliography formatting should pass: {message}")


class TestFileExtraction(unittest.TestCase):
    """Test the file extraction functionality"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_extract_groundtruth_files(self):
        """Test extracting files from tar.gz archive"""
        # Create a test tar.gz file
        tar_path = os.path.join(self.test_dir, "files.tar.gz")
        my_paper_dir = os.path.join(self.test_dir, "temp_my_paper")
        os.makedirs(my_paper_dir)
        
        # Create test files
        with open(os.path.join(my_paper_dir, "test.tex"), 'w') as f:
            f.write("\\section{Test}\n")
        
        # Create tar.gz
        with tarfile.open(tar_path, 'w:gz') as tar:
            tar.add(my_paper_dir, arcname="my_paper")
        
        # Clean up temporary directory
        shutil.rmtree(my_paper_dir)
        
        # Test extraction
        workspace, was_extracted = extract_groundtruth_files(self.test_dir)
        
        self.assertTrue(was_extracted, "Files should be extracted")
        self.assertTrue(os.path.exists(os.path.join(workspace, "my_paper", "test.tex")))


def run_comprehensive_tests():
    """Run all tests and provide detailed output"""
    print("Running comprehensive tests for paper-checker evaluation...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestPaperCheckerEvaluation))
    suite.addTests(loader.loadTestsFromTestCase(TestFileExtraction))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall result: {'✓ PASSED' if success else '✗ FAILED'}")
    
    return success


if __name__ == "__main__":
    run_comprehensive_tests()