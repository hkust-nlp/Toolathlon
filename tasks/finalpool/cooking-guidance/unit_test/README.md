# Cooking Guidance Task - Evaluation Analysis & Unit Tests

## Overview

This directory contains unit tests for the cooking-guidance task evaluation system. The evaluation checks whether an AI agent successfully:

1. **Recommends 3 dishes** based on available ingredients
2. **Utilizes >= 80%** of pantry ingredients in the selected recipes
3. **Generates accurate shopping list** covering >= 90% of missing ingredients

## ✅ **RECENT UPDATES** (Updated 2025-08-07)

### **Chinese Ingredient Names**
- **Issue**: Original ingredients used English names causing matching problems
- **Fix**: Updated `ingredients.csv` to use Chinese names while keeping English column headers
- **Example**: `Potatoes` → `土豆`, `Pork` → `猪肉`, `Garlic sprouts` → `蒜苗`

### **Quantity Comparison Logic Added** 🆕
- **Issue**: System only checked ingredient presence, not sufficiency
- **Fix**: Added comprehensive quantity parsing and comparison
- **Features**:
  - Parse numeric quantities (`4个`, `500g`, `2根`)
  - Compare available vs required amounts
  - Handle different units with safety checks
  - Support qualitative quantities (`适量`, `少许`)

### **Enhanced Evaluation Flow**
Now ingredients are categorized into:
1. **Sufficient**: Have enough quantity in pantry → Mark as used
2. **Insufficient**: Have ingredient but not enough → Add to shopping list
3. **Missing**: Don't have ingredient at all → Add to shopping list

## ✅ **PREVIOUS FIXES**

### **Critical Bug Fixed**: `parse_ingredients_csv()` 
- **Issue**: Function was reading CSV but never populating the return dictionary
- **Fix**: Added proper dictionary population in the parsing loop
- **Impact**: Now correctly extracts pantry ingredients for usage calculations

### **Ingredient Normalization System Added**
- **Issue**: Duplicate ingredients like `蒜`/`大蒜` were treated separately
- **Fix**: Added comprehensive normalization mapping for Chinese ingredients
- **Features**: 
  - Synonym mapping (大蒜→蒜, 青椒→辣椒, 猪肉片→猪肉, etc.)
  - Parenthetical description removal
  - Consistent ingredient matching

### **Recipe Parsing Artifacts Filtering**
- **Issue**: MCP server returned malformed entries like `"青茄子的数量 = 份数"`
- **Fix**: Added validation to filter out parsing artifacts
- **Patterns Filtered**:
  - Contains `=` (parsing artifacts)
  - Contains `份数`, `数量` (serving size artifacts)
  - Ends with `约` (approximately)
  - Only punctuation/numbers

## Current Evaluation Logic Flow

### **1. Data Collection**
```python
# Parse pantry ingredients (now in Chinese)
current_ingredients = {'鸡蛋': '4', '土豆': '4', '茄子': '2', '蒜苗': '2', '冬瓜': '500g', ...}

# Parse shopping list
shopping_list = {'青椒': '2个', '葱': '1根', '姜': '1块', ...}

# Get recipe requirements (cleaned and normalized)
required_ingredients = {'辣椒': '2个', '土豆': '3个', '猪肉': '300g', '蒜': '3瓣', ...}
```

### **2. Quantity-Aware Matching**
```python
for required_ingredient, required_qty in required_ingredients.items():
    for pantry_ingredient, pantry_qty in pantry_ingredients.items():
        if ingredients_match(required_ingredient, pantry_ingredient):
            if is_sufficient_quantity(pantry_qty, required_qty):
                # ✅ Sufficient: Mark as used, don't add to shopping
                used_from_pantry.add(pantry_ingredient)
            else:
                # ⚠️ Insufficient: Add to missing list for shopping
                missing_ingredients[required_ingredient] = required_qty
```

### **3. Example Matching Results**
```
Recipe needs '土豆': '3个' → Have '土豆': '4' → ✅ Sufficient (4 >= 3)
Recipe needs '辣椒': '2个' → Have '干辣椒': '50g' → ❌ Different units, need to buy
Recipe needs '猪肉': '300g' → Have '瘦猪肉片': '400g' + '五花肉': '200g' → ✅ Sufficient (600g >= 300g)
Recipe needs '蒜': '3瓣' → Have '蒜苗': '2' → ⚠️ Insufficient (need 3, have 2)
```

## Unit Test Structure

### `test_components.py` ✅ **UPDATED** (23 tests)
Tests individual functions in isolation:

- **CSV Parsing Tests**: ✅ Updated for Chinese ingredient names
- **JSON Parsing Tests**: ✅ Unchanged (was working)
- **🆕 Ingredient Normalization Tests**: Tests synonym mapping and cleaning
- **🆕 Quantity Handling Tests**: Tests parsing and comparison logic
- **Recipe Retrieval Tests**: ✅ Fixed async mocking issues
- **Main Evaluation Tests**: ✅ Updated for new workflow

### Test Results: ✅ **ALL 23 TESTS PASSING**

```
✅ ALL UNIT TESTS PASSED (23 tests)
- CSV parsing: 5 tests
- JSON parsing: 5 tests  
- Ingredient normalization: 3 tests
- 🆕 Quantity handling: 3 tests
- Recipe retrieval: 2 tests
- Main evaluation: 5 tests
```

## New Quantity Functions

### `extract_numeric_quantity(quantity_str)`
```python
extract_numeric_quantity("4个")    # → 4.0
extract_numeric_quantity("500g")   # → 500.0
extract_numeric_quantity("适量")   # → 1.0 (qualitative)
```

### `is_sufficient_quantity(available, required)`
```python
is_sufficient_quantity("4个", "3个")      # → True (have more)
is_sufficient_quantity("2个", "4个")      # → False (not enough)  
is_sufficient_quantity("4个", "500g")     # → False (different units)
is_sufficient_quantity("100g", "适量")    # → True (have some for qualitative)
```

## Expected Improvements

With Chinese names and quantity logic:

1. **Better ingredient matching** with Chinese names throughout
2. **Quantity-aware evaluation** distinguishing sufficient vs insufficient
3. **More accurate shopping lists** only including truly needed items
4. **Detailed quantity reporting** showing what's needed vs available
5. **Proper handling of units** (个, 根, g, ml, etc.)

The evaluation should now properly handle scenarios like:
- Having `土豆: 4个` but recipe needs `土豆: 6个` → Add `土豆: 2个` to shopping list
- Having `猪肉: 400g` when recipe needs `猪肉: 200g` → Don't add to shopping list
- Having `蒜苗: 2根` when recipe needs `蒜: 适量` → Sufficient (qualitative need met)

## Running Tests

```bash
# Run all tests  
cd tasks/finalpool/cooking-guidance/unit_test
python run_tests.py

# Run specific test suites
python test_components.py
python test_end_to_end.py
```