import random
from typing import List, Dict, Any


def generate_all_expense_claims(
    employees_with_errors: List[Dict[str, Any]],
    employees_no_errors: List[Dict[str, Any]],
    policy: Dict[str, Any],
    fixed_seed: int,
    generate_claims_for_employee,
    inject_form_errors
) -> List[Dict[str, Any]]:
    """Generate expense claims for all employees.
    
    Args:
        employees_with_errors: Employees that should have errors in their claims
        employees_no_errors: Employees that should have clean claims
        policy: Policy standards
        fixed_seed: Random seed for reproducibility
        generate_claims_for_employee: Function to generate claims for an employee
        inject_form_errors: Function to inject form errors
    
    Returns:
        List of all generated expense claims
    """
    rng = random.Random(fixed_seed)
    generated_claims = []
    next_seq = 1
    
    # Generate claims with errors for EMP001-EMP004
    for emp in employees_with_errors:
        emp_claims, next_seq = generate_claims_for_employee(emp, policy, next_seq, rng)
        generated_claims.extend(emp_claims)
    
    # Inject form errors for these claims (policy violations are already set)
    inject_form_errors(generated_claims, rng)
    
    # Generate claims without errors for EMP005-EMP008
    for emp in employees_no_errors:
        emp_claims, next_seq = generate_claims_for_employee(emp, policy, next_seq, rng)
        # Clear any violations and errors to ensure no errors
        for claim in emp_claims:
            claim['_policy_violations'] = []
            claim['_form_errors'] = []
        generated_claims.extend(emp_claims)
    
    return generated_claims