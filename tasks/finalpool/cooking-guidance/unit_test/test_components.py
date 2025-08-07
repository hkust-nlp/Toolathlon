#!/usr/bin/env python3
"""
Unit tests for individual evaluation components of cooking-guidance task
Tests specific functions and edge cases in isolation
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
    
    from check_local import (
        parse_ingredients_csv,
        parse_shopping_list_csv,
        extract_dish_names_from_cuisine_json,
        get_recipe_ingredients,
        check_local,
        normalize_ingredient_name,
        is_valid_ingredient,
        clean_required_ingredients,
        extract_numeric_quantity,
        get_quantity_unit,
        is_sufficient_quantity
    )
    EVALUATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import evaluation functions: {e}")
    EVALUATION_AVAILABLE = False


class TestCsvParsing(unittest.TestCase):
    """Test CSV parsing functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_parse_ingredients_csv_valid_fixed(self):
        """Test parsing valid ingredients CSV with the bug fix"""
        csv_file = self.temp_path / "ingredients.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Category', 'Ingredient Name', 'Quantity'])
            writer.writerow(['蔬菜', '土豆', '4'])
            writer.writerow(['肉类', '猪肉', '200g'])
        
        result = parse_ingredients_csv(str(csv_file))
        # Now the function should work correctly with Chinese names
        expected = {'土豆': '4', '猪肉': '200g'}
        self.assertEqual(result, expected)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_parse_ingredients_csv_missing_file(self):
        """Test parsing non-existent ingredients CSV"""
        result = parse_ingredients_csv("/nonexistent/file.csv")
        self.assertEqual(result, {})
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_parse_shopping_list_csv_valid(self):
        """Test parsing valid shopping list CSV"""
        csv_file = self.temp_path / "shopping.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Ingredient Name', 'Quantity'])
            writer.writerow(['生抽', '适量'])
            writer.writerow(['糖', '100g'])
        
        result = parse_shopping_list_csv(str(csv_file))
        expected = {'生抽': '适量', '糖': '100g'}
        self.assertEqual(result, expected)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_parse_shopping_list_csv_empty_rows(self):
        """Test parsing shopping list CSV with empty rows"""
        csv_file = self.temp_path / "shopping.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Ingredient Name', 'Quantity'])
            writer.writerow(['生抽', '适量'])
            writer.writerow(['', ''])  # Empty row
            writer.writerow(['糖', '100g'])
        
        result = parse_shopping_list_csv(str(csv_file))
        expected = {'生抽': '适量', '糖': '100g'}
        self.assertEqual(result, expected)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_parse_shopping_list_csv_missing_file(self):
        """Test parsing non-existent shopping list CSV"""
        result = parse_shopping_list_csv("/nonexistent/file.csv")
        self.assertEqual(result, {})


class TestJsonParsing(unittest.TestCase):
    """Test JSON parsing functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_extract_dish_names_valid(self):
        """Test extracting dish names from valid cuisine.json"""
        cuisine_data = {
            "example": "炒年糕",
            "recommend_cuisine1": "蒜苗炒肉",
            "recommend_cuisine2": "糖醋茄子",
            "recommend_cuisine3": "冬瓜排骨汤"
        }
        
        json_file = self.temp_path / "cuisine.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(cuisine_data, f, ensure_ascii=False)
        
        result = extract_dish_names_from_cuisine_json(str(self.temp_path))
        expected = ["蒜苗炒肉", "糖醋茄子", "冬瓜排骨汤"]
        self.assertEqual(result, expected)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_extract_dish_names_partial(self):
        """Test extracting dish names with some missing recommendations"""
        cuisine_data = {
            "example": "炒年糕",
            "recommend_cuisine1": "蒜苗炒肉",
            "recommend_cuisine2": "",
            "recommend_cuisine3": "冬瓜排骨汤"
        }
        
        json_file = self.temp_path / "cuisine.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(cuisine_data, f, ensure_ascii=False)
        
        result = extract_dish_names_from_cuisine_json(str(self.temp_path))
        expected = ["蒜苗炒肉", "冬瓜排骨汤"]
        self.assertEqual(result, expected)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_extract_dish_names_missing_file(self):
        """Test extracting dish names when cuisine.json is missing"""
        result = extract_dish_names_from_cuisine_json(str(self.temp_path))
        self.assertEqual(result, [])
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_extract_dish_names_invalid_json(self):
        """Test extracting dish names from invalid JSON"""
        json_file = self.temp_path / "cuisine.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write("{ invalid json }")
        
        result = extract_dish_names_from_cuisine_json(str(self.temp_path))
        self.assertEqual(result, [])
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_extract_dish_names_missing_keys(self):
        """Test extracting dish names when required keys are missing"""
        cuisine_data = {
            "example": "炒年糕",
            "other_key": "some_value"
        }
        
        json_file = self.temp_path / "cuisine.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(cuisine_data, f, ensure_ascii=False)
        
        result = extract_dish_names_from_cuisine_json(str(self.temp_path))
        self.assertEqual(result, [])


class TestIngredientNormalization(unittest.TestCase):
    """Test ingredient normalization and cleaning functions"""
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_normalize_ingredient_name(self):
        """Test ingredient name normalization"""
        # Test synonym mapping
        self.assertEqual(normalize_ingredient_name("大蒜"), "蒜")
        self.assertEqual(normalize_ingredient_name("蒜头"), "蒜")
        self.assertEqual(normalize_ingredient_name("大葱"), "葱")
        self.assertEqual(normalize_ingredient_name("青椒"), "辣椒")
        self.assertEqual(normalize_ingredient_name("猪肉片"), "猪肉")
        self.assertEqual(normalize_ingredient_name("马铃薯"), "土豆")
        
        # Test parenthetical removal
        self.assertEqual(normalize_ingredient_name("蒜苗（韭黄）"), "蒜苗")
        self.assertEqual(normalize_ingredient_name("猪肉(切片)"), "猪肉")
        
        # Test unchanged items
        self.assertEqual(normalize_ingredient_name("生抽"), "生抽")
        self.assertEqual(normalize_ingredient_name("盐"), "盐")
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_is_valid_ingredient(self):
        """Test ingredient validity checking"""
        # Valid ingredients
        self.assertTrue(is_valid_ingredient("猪肉"))
        self.assertTrue(is_valid_ingredient("生抽"))
        self.assertTrue(is_valid_ingredient("蒜苗"))
        
        # Invalid parsing artifacts
        self.assertFalse(is_valid_ingredient("青茄子的数量 = 份数"))
        self.assertFalse(is_valid_ingredient("面粉 = 青茄子数量"))
        self.assertFalse(is_valid_ingredient("西红柿 ="))
        self.assertFalse(is_valid_ingredient("淀粉 = 面粉 /"))
        self.assertFalse(is_valid_ingredient("葱花（一根,约"))
        
        # Edge cases
        self.assertFalse(is_valid_ingredient(""))
        self.assertFalse(is_valid_ingredient(None))
        self.assertFalse(is_valid_ingredient("123"))
        self.assertFalse(is_valid_ingredient("（）"))
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_clean_required_ingredients(self):
        """Test cleaning of recipe ingredient data"""
        dirty_ingredients = {
            "猪肉": "200g",
            "大蒜": "3瓣",
            "蒜": "2瓣",  # Should merge with 大蒜
            "青茄子的数量 = 份数": "1",  # Should be filtered out
            "面粉 = 青茄子数量": "适量",  # Should be filtered out
            "生抽": "适量",
            "盐": "少许",
            "葱花（一根,约": "1根"  # Should be filtered out
        }
        
        cleaned = clean_required_ingredients(dirty_ingredients)
        
        # Should have merged duplicates and filtered invalid entries
        expected_keys = {"猪肉", "蒜", "生抽", "盐"}
        self.assertEqual(set(cleaned.keys()), expected_keys)
        self.assertIn("蒜", cleaned)  # 大蒜 should be normalized to 蒜
        self.assertNotIn("青茄子的数量 = 份数", cleaned)
        self.assertNotIn("面粉 = 青茄子数量", cleaned)


class TestQuantityHandling(unittest.TestCase):
    """Test quantity parsing and comparison functions"""
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_extract_numeric_quantity_complex(self):
        """Test numeric quantity extraction with complex strings"""
        # Test complex recipe patterns
        self.assertEqual(extract_numeric_quantity("- 土豆 240g（越细越长更好）"), 240.0)
        self.assertEqual(extract_numeric_quantity("- 大蒜 4 瓣"), 4.0)
        self.assertEqual(extract_numeric_quantity("- 生抽 10ml"), 10.0)
        
        # Test various formats
        self.assertEqual(extract_numeric_quantity("鸡蛋 1 个（可选,不习惯的人可能会有点腥）"), 1.0)
        self.assertEqual(extract_numeric_quantity("葱姜末（姜 3-4 片约 30g"), 3.0)  # Takes first number
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_get_quantity_unit(self):
        """Test unit extraction"""
        self.assertEqual(get_quantity_unit("4个"), "个")
        self.assertEqual(get_quantity_unit("500g"), "g")
        self.assertEqual(get_quantity_unit("30ml"), "ml")
        self.assertEqual(get_quantity_unit("2根"), "根")
        
        # Test no unit cases
        self.assertEqual(get_quantity_unit("适量"), "")
        self.assertEqual(get_quantity_unit("4"), "")
        self.assertEqual(get_quantity_unit(""), "")
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_is_sufficient_quantity(self):
        """Test quantity sufficiency comparison"""
        # Test sufficient cases
        self.assertTrue(is_sufficient_quantity("4个", "3个"))    # Have more
        self.assertTrue(is_sufficient_quantity("4个", "4个"))    # Exact match
        self.assertTrue(is_sufficient_quantity("500g", "400g"))  # Sufficient weight
        
        # Test insufficient cases  
        self.assertFalse(is_sufficient_quantity("2个", "4个"))   # Not enough
        self.assertFalse(is_sufficient_quantity("300g", "500g")) # Not enough weight
        
        # Test different units (should be insufficient for safety)
        self.assertFalse(is_sufficient_quantity("4个", "500g"))  # Different units
        
        # Test qualitative requirements (should be satisfied if we have any)
        self.assertTrue(is_sufficient_quantity("2个", "适量"))   # Have some for "appropriate amount"
        self.assertTrue(is_sufficient_quantity("100g", "少许"))  # Have some for "a little"
        
        # Test no available quantity
        self.assertFalse(is_sufficient_quantity("0", "4个"))     # Have nothing
        
        # Test edge cases
        self.assertFalse(is_sufficient_quantity("", "4个"))      # Empty available
        self.assertTrue(is_sufficient_quantity("4个", ""))       # Empty required (nothing needed)


class TestRecipeRetrieval(unittest.TestCase):
    """Test recipe retrieval functions"""
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    @patch('check_local.MCPServerManager')
    @patch('check_local.call_tool_with_retry')
    def test_get_recipe_ingredients_success(self, mock_call_tool, mock_manager):
        """Test successful recipe ingredient retrieval"""
        import asyncio
        
        # Mock the MCP server response
        mock_result = AsyncMock()
        mock_result.content = [AsyncMock()]
        mock_result.content[0].text = json.dumps({
            "ingredients": [
                {"name": "猪肉", "text_quantity": "200g"},
                {"name": "蒜苗", "text_quantity": "100g"},
                {"name": "生抽", "text_quantity": "适量"}
            ]
        })
        
        # Create a coroutine that returns the mock result
        async def mock_call():
            return mock_result
        
        mock_call_tool.return_value = mock_call()
        
        # Mock server manager
        mock_server = AsyncMock()
        mock_manager.return_value.servers = {'howtocook': mock_server}
        
        # Test the function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        dish_names = ["蒜苗炒肉"]
        result = loop.run_until_complete(get_recipe_ingredients(dish_names))
        required_ingredients, found_recipes, recipe_details = result
        
        loop.close()
        
        self.assertEqual(found_recipes, ["蒜苗炒肉"])
        self.assertIn("猪肉", required_ingredients)
        self.assertIn("蒜苗", required_ingredients)
        self.assertIn("生抽", required_ingredients)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    @patch('check_local.MCPServerManager')
    @patch('check_local.call_tool_with_retry')
    def test_get_recipe_ingredients_timeout(self, mock_call_tool, mock_manager):
        """Test recipe retrieval with timeout"""
        import asyncio
        
        # Create a coroutine that raises TimeoutError
        async def mock_timeout():
            raise asyncio.TimeoutError()
            
        mock_call_tool.return_value = mock_timeout()
        
        # Mock server manager
        mock_server = AsyncMock()
        mock_manager.return_value.servers = {'howtocook': mock_server}
        
        # Test the function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        dish_names = ["蒜苗炒肉"]
        result = loop.run_until_complete(get_recipe_ingredients(dish_names))
        required_ingredients, found_recipes, recipe_details = result
        
        loop.close()
        
        self.assertEqual(found_recipes, [])
        self.assertEqual(required_ingredients, {})


class TestMainEvaluation(unittest.TestCase):
    """Test main evaluation function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create perfect workspace
        self.perfect_workspace = self.temp_path / "perfect"
        self.perfect_workspace.mkdir()
        
        # Copy perfect workspace files
        perfect_source = base_dir / "perfect_workspace"
        if perfect_source.exists():
            import shutil
            shutil.copytree(perfect_source, self.perfect_workspace, dirs_exist_ok=True)
        else:
            # Create minimal perfect workspace if source doesn't exist
            self.create_minimal_perfect_workspace()
    
    def create_minimal_perfect_workspace(self):
        """Create minimal perfect workspace for testing"""
        # Create ingredients.csv
        with open(self.perfect_workspace / "ingredients.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Category', 'Ingredient Name', 'Quantity'])
            writer.writerow(['Vegetables', 'Potatoes', '4'])
            writer.writerow(['Vegetables', 'Eggplant', '2'])
            writer.writerow(['Meat', 'Pork', '200g'])
        
        # Create cuisine.json
        cuisine_data = {
            "example": "炒年糕",
            "recommend_cuisine1": "蒜苗炒肉",
            "recommend_cuisine2": "糖醋茄子",
            "recommend_cuisine3": "冬瓜排骨汤"
        }
        with open(self.perfect_workspace / "cuisine.json", 'w', encoding='utf-8') as f:
            json.dump(cuisine_data, f, ensure_ascii=False)
        
        # Create shopping.csv
        with open(self.perfect_workspace / "shopping.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Ingredient Name', 'Quantity'])
            writer.writerow(['生抽', '适量'])
            writer.writerow(['糖', '100g'])
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_missing_files_fail(self):
        """Test that missing required files cause evaluation to fail"""
        empty_workspace = self.temp_path / "empty"
        empty_workspace.mkdir()
        
        success, error = check_local(str(empty_workspace), str(self.perfect_workspace))
        self.assertFalse(success)
        self.assertIn("shopping.csv", error)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_missing_ingredients_file(self):
        """Test missing ingredients.csv file"""
        incomplete_workspace = self.temp_path / "incomplete"
        incomplete_workspace.mkdir()
        
        # Create only shopping.csv and cuisine.json
        with open(incomplete_workspace / "shopping.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Ingredient Name', 'Quantity'])
        
        cuisine_data = {"recommend_cuisine1": "test", "recommend_cuisine2": "test", "recommend_cuisine3": "test"}
        with open(incomplete_workspace / "cuisine.json", 'w', encoding='utf-8') as f:
            json.dump(cuisine_data, f)
        
        success, error = check_local(str(incomplete_workspace), str(self.perfect_workspace))
        self.assertFalse(success)
        self.assertIn("ingredients.csv", error)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_missing_cuisine_file(self):
        """Test missing cuisine.json file"""
        incomplete_workspace = self.temp_path / "incomplete"
        incomplete_workspace.mkdir()
        
        # Create only shopping.csv and ingredients.csv
        with open(incomplete_workspace / "shopping.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Ingredient Name', 'Quantity'])
        
        with open(incomplete_workspace / "ingredients.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Category', 'Ingredient Name', 'Quantity'])
        
        success, error = check_local(str(incomplete_workspace), str(self.perfect_workspace))
        self.assertFalse(success)
        self.assertIn("cuisine.json", error)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_empty_shopping_list(self):
        """Test empty shopping list"""
        test_workspace = self.temp_path / "empty_shopping"
        test_workspace.mkdir()
        
        # Copy ingredients and cuisine files
        import shutil
        shutil.copy2(self.perfect_workspace / "ingredients.csv", test_workspace)
        shutil.copy2(self.perfect_workspace / "cuisine.json", test_workspace)
        
        # Create empty shopping list
        with open(test_workspace / "shopping.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Ingredient Name', 'Quantity'])
        
        success, error = check_local(str(test_workspace), str(self.perfect_workspace))
        self.assertFalse(success)
        self.assertIn("empty", error)
    
    @unittest.skipUnless(EVALUATION_AVAILABLE, "Evaluation functions not available")
    def test_insufficient_dish_count(self):
        """Test insufficient number of recommended dishes"""
        test_workspace = self.temp_path / "insufficient_dishes"
        test_workspace.mkdir()
        
        # Copy ingredients and shopping files
        import shutil
        shutil.copy2(self.perfect_workspace / "ingredients.csv", test_workspace)
        shutil.copy2(self.perfect_workspace / "shopping.csv", test_workspace)
        
        # Create cuisine.json with insufficient dishes
        cuisine_data = {
            "example": "炒年糕",
            "recommend_cuisine1": "蒜苗炒肉",
            "recommend_cuisine2": "",
            "recommend_cuisine3": ""
        }
        with open(test_workspace / "cuisine.json", 'w', encoding='utf-8') as f:
            json.dump(cuisine_data, f, ensure_ascii=False)
        
        success, error = check_local(str(test_workspace), str(self.perfect_workspace))
        self.assertFalse(success)
        self.assertIn("Expected 3 dishes", error)


def run_unit_tests():
    """Run all unit tests with colored output"""
    
    print("🧪 Cooking Guidance - Unit Tests")
    print("=" * 60)
    
    if not EVALUATION_AVAILABLE:
        print("❌ Cannot run tests: Evaluation functions not available")
        print("   Make sure the evaluation module can be imported")
        return False
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCsvParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestJsonParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestIngredientNormalization))
    suite.addTests(loader.loadTestsFromTestCase(TestQuantityHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestRecipeRetrieval))
    suite.addTests(loader.loadTestsFromTestCase(TestMainEvaluation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print(f"✅ ALL UNIT TESTS PASSED ({result.testsRun} tests)")
    else:
        print(f"❌ SOME TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        for test, error in result.failures + result.errors:
            print(f"   {test}: {error.split(chr(10))[0]}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_unit_tests()
    sys.exit(0 if success else 1)