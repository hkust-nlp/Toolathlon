# Cooking Guidance Task - Evaluation Analysis & Unit Tests

## Overview

This directory contains unit tests for the cooking-guidance task evaluation system. The evaluation checks whether an AI agent successfully:

1. **Recommends 3 dishes** based on available ingredients
2. **Utilizes >= 80%** of pantry ingredients in the selected recipes
3. **Generates accurate shopping list** covering >= 90% of missing ingredients

## Evaluation Logic Analysis

### Core Components

#### 1. File Parsing (`check_local.py:9-37`)
- **`parse_ingredients_csv()`**: Parses available pantry ingredients
  - ⚠️ **BUG FOUND**: Function reads CSV but doesn't populate return dictionary (line 18-19)
  - Returns empty dict instead of ingredient mapping
- **`parse_shopping_list_csv()`**: Parses generated shopping list
  - ✅ **Works correctly**: Properly extracts ingredient-quantity pairs

#### 2. Dish Extraction (`check_local.py:39-68`)
- **`extract_dish_names_from_cuisine_json()`**: Extracts 3 recommended dishes
  - ✅ **Works correctly**: Validates JSON format and extracts `recommend_cuisine1-3`
  - Handles missing/empty recommendations gracefully

#### 3. Recipe Validation (`check_local.py:70-134`)
- **`get_recipe_ingredients()`**: Retrieves recipe data via MCP howtocook server
  - ✅ **Robust**: Implements retry logic (3 attempts) with timeout handling
  - Validates recipe data structure and extracts ingredient requirements
  - Cleans ingredient names by removing parenthetical descriptions

#### 4. Main Evaluation (`check_local.py:136-261`)
- **Usage Rate Check**: Validates >= 80% pantry ingredient utilization
  - Uses flexible substring matching for ingredient names
- **Coverage Check**: Ensures >= 90% shopping list coverage of missing ingredients
- **Edge Case**: Handles scenario where no ingredients are missing (shopping list should be empty)

### Key Evaluation Criteria

1. **File Presence**: All 3 files must exist (`ingredients.csv`, `cuisine.json`, `shopping.csv`)
2. **Dish Count**: Exactly 3 dishes must be recommended
3. **Recipe Validation**: All 3 dishes must have findable recipes via MCP server
4. **Usage Rate**: >= 80% of pantry ingredients must be used in selected recipes
5. **Shopping Coverage**: >= 90% of missing ingredients must appear in shopping list
6. **Empty Shopping**: If no ingredients missing, shopping list must be empty

## Unit Test Structure

### `test_components.py`
Tests individual functions in isolation:

- **CSV Parsing Tests**: Valid files, missing files, empty rows
- **JSON Parsing Tests**: Valid cuisine data, partial data, invalid JSON, missing files
- **Recipe Retrieval Tests**: Successful retrieval, timeouts, server errors (mocked)
- **Main Evaluation Tests**: File validation, dish counting, basic logic flow

### `test_end_to_end.py`  
Tests complete evaluation pipeline:

- **Perfect Scenarios**: High usage rate with accurate shopping list
- **Failure Scenarios**: Low usage rate, incomplete shopping coverage
- **Edge Cases**: No missing ingredients, recipe lookup failures
- **Robustness Tests**: Unicode handling, name variations, corrupted files

### `perfect_workspace/`
Contains reference files for testing:
- `ingredients.csv`: Base pantry ingredients
- `cuisine.json`: 3 recommended dishes using available ingredients
- `shopping.csv`: Missing ingredients needed for recipes

## Known Issues

### 1. Critical Bug in `parse_ingredients_csv()` 
**Location**: `check_local.py:18-19`  
**Issue**: Function reads CSV data but never populates the return dictionary  
**Impact**: Function always returns `{}`, breaking ingredient usage calculations  
**Fix Needed**: Add `current_ingredients[ingredient_name] = quantity` in the loop

### 2. Ingredient Matching Logic
**Location**: `check_local.py:212-216`  
**Issue**: Simple substring matching may cause false positives  
**Example**: "蒜" (garlic) could match "蒜苗" (garlic sprouts) incorrectly  
**Improvement**: Consider more sophisticated ingredient name normalization

### 3. MCP Server Dependency
**Issue**: Tests require mocking complex MCP server interactions  
**Impact**: Real recipe validation can't be tested without full MCP setup  
**Workaround**: Extensive mocking in unit tests, integration tests need full environment

## Running Tests

```bash
# Run all tests
cd tasks/finalpool/cooking-guidance/unit_test
python run_tests.py

# Run specific test suites
python test_components.py
python test_end_to_end.py
```

## Test Coverage

- ✅ **CSV parsing functions**
- ✅ **JSON extraction logic** 
- ✅ **File validation**
- ✅ **Error handling**
- ✅ **Edge cases and robustness**
- ⚠️ **MCP integration** (mocked only)
- ⚠️ **Real recipe matching** (requires live MCP server)

## Recommendations

1. **Fix Critical Bug**: Update `parse_ingredients_csv()` to actually populate the ingredients dictionary
2. **Improve Ingredient Matching**: Implement more sophisticated name normalization and matching
3. **Add Integration Tests**: Test with real MCP server in CI/CD pipeline
4. **Enhance Error Messages**: Provide more specific feedback for evaluation failures
5. **Add Performance Tests**: Verify evaluation completes within reasonable time limits