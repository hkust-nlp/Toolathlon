# Update Photo Task

## Overview

This task is to automatically update the featured images of WooCommerce products based on last week's sales data. The goal is to verify whether the MCP Server can analyze sales data, identify the best-selling variation for each variable product, and set that variation's image as the product's featured image.

## Task Description

Update the featured image of each WooCommerce variable product according to last week's sales data. The variation with the highest sales should have its image set as the featured image for the parent product.

### Steps

1. **Determine the Time Range**
   - Get the complete date range for last week (Monday to Sunday).
   - Use the current system time to calculate last week's start and end dates.

2. **Analyze Sales Data**
   - Iterate over all variable products.
   - For each product, get sales data for each variation during the relevant week.
   - Identify the best-selling variation for each product.

3. **Update Product Image**
   - Get the image of the top-selling variation.
   - Set this image as the parent product's featured image.
   - If the best-selling variation does not have a separate image, skip that product.

4. **Output Results**
   - Count the number of products updated successfully.
   - Provide a summary report of the operation.

## Technical Requirements

- Use the WooCommerce MCP server.
- Correctly handle date range calculation.
- Robustly deal with edge cases (e.g., no sales data, no images).
- Provide clear progress feedback.

## Expected Output

After completion, the report should include:
- The total number of products processed
- The number of products successfully updated
- The number of products skipped and the reasons
- Operation completion time

## File Structure

```
update-photo-task/
├── README.md                    # This file
├── task_config.json             # Task configuration
├── docs/
│   ├── task.md                  # Detailed task description
│   └── user_system_prompt.md    # User/system prompt
├── evaluation/
│   ├── main.py                  # Main evaluation script
│   └── check_content.py         # Content check script
├── preprocess/
│   ├── setup_test_products.py   # Test product setup
│   └── woocommerce_client.py    # WooCommerce client
├── initial_workspace/           # Initial workspace
└── groundtruth_workspace/       # Ground truth (expected results)
```