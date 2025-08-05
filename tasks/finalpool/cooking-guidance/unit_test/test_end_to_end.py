#!/usr/bin/env python3
"""
End-to-end integration tests for cooking-guidance task evaluation
Tests the complete evaluation pipeline with realistic scenarios
"""

import sys
import unittest
import tempfile
import json
import csv
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add evaluation directory to Python path
base_dir = Path(__file__).parent
evaluation_dir = base_dir.parent / "evaluation"
project_root = base_dir.parent.parent.parent.parent  # Go up to mcpbench_dev root
sys.path.insert(0, str(evaluation_dir))
sys.path.insert(0, str(project_root))

# Import evaluation functions
try:
    # Mock the MCP dependencies before importing
    import sys
    from unittest.mock import MagicMock
    
    # Create mock modules for utils.mcp
    mock_utils = MagicMock()
    mock_mcp = MagicMock()
    mock_tool_servers = MagicMock()
    mock_tool_servers.MCPServerManager = MagicMock()
    mock_tool_servers.call_tool_with_retry = MagicMock()
    
    sys.modules['utils'] = mock_utils
    sys.modules['utils.mcp'] = mock_mcp
    sys.modules['utils.mcp.tool_servers'] = mock_tool_servers
    
    from check_local import check_local, get_recipe_ingredients
    EVALUATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import evaluation functions: {e}")
    EVALUATION_AVAILABLE = False


class TestEndToEndEvaluation(unittest.TestCase):
    """Test complete evaluation pipeline with realistic scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Base ingredients available in pantry
        self.base_ingredients = [
            ['Category', 'Ingredient Name', 'Quantity'],
            ['Eggs', 'Eggs', '4'],
            ['Vegetables', 'Potatoes', '4'],
            ['Vegetables', 'Eggplant', '2'],
            ['Vegetables', 'Garlic sprouts', '2'],
            ['Vegetables', 'Winter melon', '500g'],
            ['Meat', 'Lean pork slices/Pure lean meat', '400g'],
            ['Meat', 'Pork belly/Pork', '200g'],
            ['Soup ingredients', 'Milk', '30ml'],
            ['Other', '(Dried) Chili', '50g']
        ]
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def create_workspace(self, name, ingredients=None, dishes=None, shopping_items=None):
        """Helper to create test workspace"""
        workspace = self.temp_path / name
        workspace.mkdir()
        
        # Create ingredients.csv
        ingredients_data = ingredients or self.base_ingredients
        with open(workspace / "ingredients.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(ingredients_data)
        
        # Create cuisine.json
        cuisine_data = {
            "example": "炒年糕",
            "recommend_cuisine1": dishes[0] if dishes and len(dishes) > 0 else "",
            "recommend_cuisine2": dishes[1] if dishes and len(dishes) > 1 else "",
            "recommend_cuisine3": dishes[2] if dishes and len(dishes) > 2 else ""
        }
        with open(workspace / "cuisine.json", 'w', encoding='utf-8') as f:
            json.dump(cuisine_data, f, ensure_ascii=False)
        
        # Create shopping.csv
        with open(workspace / "shopping.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Ingredient Name', 'Quantity'])
            if shopping_items:
                for item, quantity in shopping_items.items():
                    writer.writerow([item, quantity])
        
        return workspace
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    @patch('check_local.get_recipe_ingredients')
    def test_perfect_scenario_high_usage(self, mock_get_recipe):
        """Test perfect scenario with high ingredient usage rate"""
        # Mock recipe ingredients that use most of the pantry items
        mock_get_recipe.return_value = (
            {
                '猪肉': '200g',  # matches "Lean pork slices/Pure lean meat"
                '茄子': '2个',   # matches "Eggplant"  
                '蒜苗': '100g',  # matches "Garlic sprouts"
                '冬瓜': '300g',  # matches "Winter melon"
                '鸡蛋': '2个',   # matches "Eggs"
                '土豆': '2个',   # matches "Potatoes"
                '辣椒': '20g',   # matches "(Dried) Chili"
                '生抽': '适量',   # not in pantry
                '老抽': '适量',   # not in pantry
                '盐': '适量'     # not in pantry
            },
            ['蒜苗炒肉', '糖醋茄子', '冬瓜排骨汤'],
            {}
        )
        
        # Create workspace with appropriate shopping list
        workspace = self.create_workspace(
            "perfect_high_usage",
            dishes=['蒜苗炒肉', '糖醋茄子', '冬瓜排骨汤'],
            shopping_items={'生抽': '适量', '老抽': '适量', '盐': '适量'}
        )
        
        success, error = check_local(str(workspace), "")
        self.assertTrue(success, f"Perfect high usage scenario should pass: {error}")
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    @patch('check_local.get_recipe_ingredients')
    def test_low_usage_rate_fails(self, mock_get_recipe):
        """Test that low ingredient usage rate fails evaluation"""
        # Mock recipe ingredients that use very few pantry items
        mock_get_recipe.return_value = (
            {
                '猪肉': '200g',  # matches "Lean pork slices/Pure lean meat"
                '生抽': '适量',   # not in pantry
                '糖': '适量'     # not in pantry
            },
            ['蒜苗炒肉', '糖醋茄子', '冬瓜排骨汤'],
            {}
        )
        
        workspace = self.create_workspace(
            "low_usage",
            dishes=['蒜苗炒肉', '糖醋茄子', '冬瓜排骨汤'],
            shopping_items={'生抽': '适量', '糖': '适量'}
        )
        
        success, error = check_local(str(workspace), "")
        self.assertFalse(success)
        self.assertIn("usage rate", error.lower())
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    @patch('check_local.get_recipe_ingredients')
    def test_incomplete_shopping_list_fails(self, mock_get_recipe):
        """Test that incomplete shopping list fails evaluation"""
        # Mock recipe ingredients with several missing items
        mock_get_recipe.return_value = (
            {
                '猪肉': '200g',    # matches pantry
                '茄子': '2个',     # matches pantry
                '生抽': '适量',     # not in pantry
                '老抽': '适量',     # not in pantry
                '盐': '适量',      # not in pantry
                '糖': '适量',      # not in pantry
                '料酒': '适量'     # not in pantry
            },
            ['蒜苗炒肉', '糖醋茄子', '冬瓜排骨汤'],
            {}
        )
        
        # Create shopping list that's missing some items
        workspace = self.create_workspace(
            "incomplete_shopping",
            dishes=['蒜苗炒肉', '糖醋茄子', '冬瓜排骨汤'],
            shopping_items={'生抽': '适量', '老抽': '适量'}  # Missing salt, sugar, cooking wine
        )
        
        success, error = check_local(str(workspace), "")
        self.assertFalse(success)
        self.assertIn("coverage", error.lower())
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    @patch('check_local.get_recipe_ingredients')
    def test_no_missing_ingredients_empty_shopping(self, mock_get_recipe):
        """Test scenario where no ingredients are missing (empty shopping list)"""
        # Mock recipe ingredients that all exist in pantry
        mock_get_recipe.return_value = (
            {
                '猪肉': '200g',  # matches "Lean pork slices/Pure lean meat"
                '茄子': '2个',   # matches "Eggplant"
                '蒜苗': '100g',  # matches "Garlic sprouts"
                '冬瓜': '300g',  # matches "Winter melon"
                '鸡蛋': '2个',   # matches "Eggs"
                '土豆': '2个'    # matches "Potatoes"
            },
            ['蒜苗炒肉', '糖醋茄子', '冬瓜排骨汤'],
            {}
        )
        
        # Create workspace with empty shopping list
        workspace = self.create_workspace(
            "no_missing_ingredients",
            dishes=['蒜苗炒肉', '糖醋茄子', '冬瓜排骨汤'],
            shopping_items={}  # Empty shopping list
        )
        
        success, error = check_local(str(workspace), "")
        self.assertTrue(success, f"No missing ingredients scenario should pass: {error}")
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    @patch('check_local.get_recipe_ingredients')
    def test_no_missing_but_non_empty_shopping_fails(self, mock_get_recipe):
        """Test scenario where no ingredients are missing but shopping list is not empty"""
        # Mock recipe ingredients that all exist in pantry
        mock_get_recipe.return_value = (
            {
                '猪肉': '200g',  # matches "Lean pork slices/Pure lean meat"
                '茄子': '2个',   # matches "Eggplant"
                '蒜苗': '100g',  # matches "Garlic sprouts"
            },
            ['蒜苗炒肉', '糖醋茄子', '冬瓜排骨汤'],
            {}
        )
        
        # Create workspace with non-empty shopping list when none needed
        workspace = self.create_workspace(
            "unnecessary_shopping",
            dishes=['蒜苗炒肉', '糖醋茄子', '冬瓜排骨汤'],
            shopping_items={'生抽': '适量'}  # Unnecessary item
        )
        
        success, error = check_local(str(workspace), "")
        self.assertFalse(success)
        self.assertIn("not empty", error)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    @patch('check_local.get_recipe_ingredients')
    def test_recipe_not_found_fails(self, mock_get_recipe):
        """Test that missing recipes cause evaluation to fail"""
        # Mock scenario where not all recipes are found
        mock_get_recipe.return_value = (
            {'猪肉': '200g'},
            ['蒜苗炒肉'],  # Only 1 out of 3 recipes found
            {}
        )
        
        workspace = self.create_workspace(
            "missing_recipes",
            dishes=['蒜苗炒肉', '糖醋茄子', '冬瓜排骨汤'],
            shopping_items={'生抽': '适量'}
        )
        
        success, error = check_local(str(workspace), "")
        self.assertFalse(success)
        self.assertIn("could not find valid recipes", error.lower())
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_insufficient_dishes_fails(self):
        """Test that insufficient number of dishes fails evaluation"""
        workspace = self.create_workspace(
            "insufficient_dishes",
            dishes=['蒜苗炒肉'],  # Only 1 dish instead of 3
            shopping_items={'生抽': '适量'}
        )
        
        success, error = check_local(str(workspace), "")
        self.assertFalse(success)
        self.assertIn("Expected 3 dishes", error)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_corrupted_files_fail(self):
        """Test that corrupted files cause evaluation to fail"""
        workspace = self.temp_path / "corrupted"
        workspace.mkdir()
        
        # Create corrupted ingredients.csv
        with open(workspace / "ingredients.csv", 'w', encoding='utf-8') as f:
            f.write("This is not a valid CSV file")
        
        # Create valid other files
        cuisine_data = {
            "recommend_cuisine1": "蒜苗炒肉",
            "recommend_cuisine2": "糖醋茄子", 
            "recommend_cuisine3": "冬瓜排骨汤"
        }
        with open(workspace / "cuisine.json", 'w', encoding='utf-8') as f:
            json.dump(cuisine_data, f)
        
        with open(workspace / "shopping.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Ingredient Name', 'Quantity'])
            writer.writerow(['生抽', '适量'])
        
        success, error = check_local(str(workspace), "")
        self.assertFalse(success)


class TestRobustnessScenarios(unittest.TestCase):
    """Test robustness with edge cases and partial data"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_ingredient_name_variations(self):
        """Test handling of ingredient name variations"""
        workspace = self.temp_path / "variations"
        workspace.mkdir()
        
        # Test ingredients with different naming conventions
        ingredients = [
            ['Category', 'Ingredient Name', 'Quantity'],
            ['Meat', '猪肉片', '400g'],           # Chinese name
            ['Meat', 'Pork slices', '200g'],     # English name
            ['Vegetables', '土豆（马铃薯）', '4'], # With parenthetical
            ['Vegetables', 'Potato', '2']        # English equivalent
        ]
        
        with open(workspace / "ingredients.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(ingredients)
        
        cuisine_data = {
            "recommend_cuisine1": "蒜苗炒肉",
            "recommend_cuisine2": "糖醋茄子",
            "recommend_cuisine3": "冬瓜排骨汤"
        }
        with open(workspace / "cuisine.json", 'w', encoding='utf-8') as f:
            json.dump(cuisine_data, f, ensure_ascii=False)
        
        with open(workspace / "shopping.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Ingredient Name', 'Quantity'])
            writer.writerow(['生抽', '适量'])
        
        # The evaluation should handle name variations gracefully
        # This test documents current behavior - may need adjustment based on actual matching logic
        success, error = check_local(str(workspace), "")
        # We expect this to fail due to insufficient dishes, but not due to parsing errors
        self.assertFalse(success)
        self.assertIn("Expected 3 dishes", error)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_unicode_handling(self):
        """Test proper Unicode handling in all files"""
        workspace = self.temp_path / "unicode"
        workspace.mkdir()
        
        # Create files with various Unicode characters
        ingredients = [
            ['Category', 'Ingredient Name', 'Quantity'],
            ['蔬菜', '蒜苗（韭黄）', '100g'],
            ['肉类', '猪肉丝', '200g'],
            ['调料', '生抽（老抽）', '适量']
        ]
        
        with open(workspace / "ingredients.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(ingredients)
        
        cuisine_data = {
            "example": "炒年糕",
            "recommend_cuisine1": "蒜苗炒肉丝",
            "recommend_cuisine2": "糖醋茄子",
            "recommend_cuisine3": "冬瓜排骨汤"
        }
        with open(workspace / "cuisine.json", 'w', encoding='utf-8') as f:
            json.dump(cuisine_data, f, ensure_ascii=False, indent=2)
        
        with open(workspace / "shopping.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Ingredient Name', 'Quantity'])
            writer.writerow(['生抽', '适量'])
            writer.writerow(['糖', '100g'])
        
        # Should handle Unicode without crashing
        success, error = check_local(str(workspace), "")
        # Test should not fail due to encoding issues
        if not success:
            self.assertNotIn("encoding", error.lower())
            self.assertNotIn("unicode", error.lower())


def run_integration_tests():
    """Run all integration tests with colored output"""
    
    print("🔬 Cooking Guidance - Integration Tests")
    print("=" * 60)
    
    if not EVALUATION_AVAILABLE:
        print("❌ Cannot run tests: Evaluation functions not available")
        print("   Make sure the evaluation module can be imported")
        return False
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndEvaluation))
    suite.addTests(loader.loadTestsFromTestCase(TestRobustnessScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print(f"✅ ALL INTEGRATION TESTS PASSED ({result.testsRun} tests)")
    else:
        print(f"❌ SOME TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        for test, error in result.failures + result.errors:
            print(f"   {test}: {error.split(chr(10))[0]}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)