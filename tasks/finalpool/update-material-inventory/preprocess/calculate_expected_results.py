#!/usr/bin/env python3
"""
Calculate the expected results based on the generated test orders and initial inventory.
"""

import json
import os
from typing import Dict, Any

def load_json(file_path: str) -> Any:
    """Load a JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: Any, file_path: str) -> None:
    """Save data as JSON to a file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def calculate_expected_results():
    """Calculate expected results based on test orders and initial inventory"""
    
    # File paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    task_dir = os.path.dirname(current_dir)
    
    test_orders_path = os.path.join(current_dir, "test_orders.json")
    initial_config_path = os.path.join(task_dir, "task_config.json")
    output_path = os.path.join(task_dir, "groundtruth_workspace", "expected_results.json")
    
    # Load data
    test_orders = load_json(test_orders_path)
    
    # Load initial inventory and BOM data from an existing expected_results.json file
    existing_expected = load_json(output_path)
    initial_product_inventory = existing_expected["initial_inventories"]["product_inventory"]
    initial_material_inventory = existing_expected["initial_inventories"]["material_inventory"]
    bom_data = existing_expected["bom_data"]
    
    # Calculate total ordered quantity for each SKU
    total_quantities_ordered = {}
    for order in test_orders:
        for item in order["items"]:
            sku = item["sku"]
            quantity = item["quantity"]
            total_quantities_ordered[sku] = total_quantities_ordered.get(sku, 0) + quantity
    
    # Calculate material consumption
    expected_material_consumption = {}
    calculation_details = {
        "product_inventory": {},
        "material_consumption": {}
    }
    
    # Calculate material consumption for each product
    for sku, quantity in total_quantities_ordered.items():
        if sku in bom_data:
            calculation_details["material_consumption"][f"{sku}_consumption"] = {}
            for material, unit_consumption in bom_data[sku].items():
                total_consumption = quantity * unit_consumption
                expected_material_consumption[material] = expected_material_consumption.get(material, 0) + total_consumption
                calculation_details["material_consumption"][f"{sku}_consumption"][material] = f"{quantity} × {unit_consumption} = {total_consumption}"
    
    # Calculate final inventories
    expected_final_woocommerce = {}
    expected_final_material = {}
    
    # Calculate material inventory deduction
    calculation_details["material_consumption"]["material_inventory_deduction"] = {}
    for material, initial_qty in initial_material_inventory.items():
        consumed_qty = expected_material_consumption.get(material, 0)
        final_qty = initial_qty - consumed_qty
        expected_final_material[material] = final_qty
        calculation_details["material_consumption"]["material_inventory_deduction"][material] = f"{initial_qty} - {consumed_qty} = {final_qty}"

    # Calculate remaining product inventory based on material constraints (can produce with current materials)
    for sku, initial_qty in initial_product_inventory.items():
        bom_data_sku = bom_data[sku]
        material_constraints = []
        for material, unit_consumption in bom_data_sku.items():
            if material in expected_final_material:
                available_material = expected_final_material[material]
                max_production_for_material = available_material / unit_consumption
                material_constraints.append(max_production_for_material)
        # Use the most restrictive (minimum) among all materials, round down to integer
        sku_max_production = int(min(material_constraints)) if material_constraints else 0
        expected_final_woocommerce[sku] = sku_max_production

    # Build the expected results dictionary
    expected_results = {
        "task_description": "Groundtruth for update material inventory task",
        "test_orders_summary": {
            "total_quantities_ordered": total_quantities_ordered
        },
        "initial_inventories": {
            "product_inventory": initial_product_inventory,
            "material_inventory": initial_material_inventory
        },
        "bom_data": bom_data,
        "expected_material_consumption": expected_material_consumption,
        "expected_final_inventories": {
            "woocommerce_inventory": expected_final_woocommerce,
            "google_sheets_material_inventory": expected_final_material
        },
        "calculation_details": calculation_details,
        "evaluation_criteria": {
            "description": "Check if the agent correctly updates the WooCommerce product inventory and Google Sheets material inventory after processing orders",
            "woocommerce_tolerance": 0,
            "material_inventory_tolerance": 0.01,
            "required_accuracy": "100%"
        }
    }
    
    # Save the expected results
    save_json(expected_results, output_path)
    print(f"Expected results calculated and saved to: {output_path}")
    
    # Print summary
    print("\nOrder summary:")
    for sku, qty in total_quantities_ordered.items():
        print(f"  {sku}: {qty}")
    
    print("\nMaterial consumption:")
    for material, consumption in expected_material_consumption.items():
        print(f"  {material}: {consumption}")

if __name__ == "__main__":
    calculate_expected_results()