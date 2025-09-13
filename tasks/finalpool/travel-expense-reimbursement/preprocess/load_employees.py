import json
import os
from typing import List, Dict, Any


def load_employees_from_mapping_files(groundtruth_dir: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load employees from both manager mapping files.
    
    Returns:
        - employees_with_errors: List of employees from manager_mapping.json (EMP001-EMP004)
        - employees_no_errors: List of employees from manager_mapping_no_error.json (EMP005-EMP008)
    """
    mapping_with_errors_path = os.path.join(groundtruth_dir, "manager_mapping.json")
    mapping_no_errors_path = os.path.join(groundtruth_dir, "manager_mapping_no_error.json")
    
    # Read employees with errors (EMP001-EMP004)
    with open(mapping_with_errors_path, 'r', encoding='utf-8') as f:
        mapping_with_errors = json.load(f)
    
    # Read employees without errors (EMP005-EMP008)
    with open(mapping_no_errors_path, 'r', encoding='utf-8') as f:
        mapping_no_errors = json.load(f)
    
    # Department and level mappings for all employees
    dept_level_map = {
        'EMP001': {'level': 'L3', 'department': 'Sales Department'},
        'EMP002': {'level': 'L2', 'department': 'Technology Department'},
        'EMP003': {'level': 'L4', 'department': 'Marketing Department'},
        'EMP004': {'level': 'L1', 'department': 'Finance Department'},
        'EMP005': {'level': 'L3', 'department': 'Sales Department'},
        'EMP006': {'level': 'L2', 'department': 'Technology Department'},
        'EMP007': {'level': 'L4', 'department': 'Marketing Department'},
        'EMP008': {'level': 'L1', 'department': 'Finance Department'},
    }
    
    # Extract employees with errors
    employees_with_errors = []
    for group in mapping_with_errors['groups']:
        for emp in group['employees']:
            emp_data = {
                'employee_id': emp['employee_id'],
                'employee_name': emp['employee_name'],
                'employee_email': emp['email'],
                'employee_level': dept_level_map[emp['employee_id']]['level'],
                'department': dept_level_map[emp['employee_id']]['department'],
                'manager_email': group['manager']['email']
            }
            employees_with_errors.append(emp_data)
    
    # Extract employees without errors
    employees_no_errors = []
    for group in mapping_no_errors['groups']:
        for emp in group['employees']:
            emp_data = {
                'employee_id': emp['employee_id'],
                'employee_name': emp['employee_name'],
                'employee_email': emp['email'],
                'employee_level': dept_level_map[emp['employee_id']]['level'],
                'department': dept_level_map[emp['employee_id']]['department'],
                'manager_email': group['manager']['email']
            }
            employees_no_errors.append(emp_data)
    
    return employees_with_errors, employees_no_errors