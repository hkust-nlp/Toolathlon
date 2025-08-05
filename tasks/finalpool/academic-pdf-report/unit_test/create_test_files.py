#!/usr/bin/env python3
"""
Create test Excel files for different evaluation scenarios
"""

import pandas as pd
from pathlib import Path

def create_test_workspaces():
    """Create 5 test workspaces with different Excel file scenarios"""
    
    base_dir = Path(__file__).parent
    
    # Test Workspace 1: Perfect Excel (all correct)
    perfect_data = [
        {
            "Title": "Strategy Coopetition Explains the Emergence and Transience of In-Context Learning",
            "First Author": "Aaditya K Singh",
            "Affiliation": "Gatsby Computational Neuroscience Unit, University College London",
            "Personal Website": "https://scholar.google.com/citations?user=9OPKqmMAAAAJ"
        },
        {
            "Title": "Model Immunization from a Condition Number Perspective",
            "First Author": "Amber Yijia Zheng",
            "Affiliation": "Department of Computer Science, Purdue University",
            "Personal Website": "https://scholar.google.com/citations?user=SZQIVG0AAAAJ"
        },
        {
            "Title": "Flowing Datasets with Wasserstein over Wasserstein Gradient Flows",
            "First Author": "Clément Bonet",
            "Affiliation": "ENSAE, CREST, IP Paris",
            "Personal Website": "https://scholar.google.com/citations?user=wjCPk5kAAAAJ"
        },
        {
            "Title": "Learning with Expected Signatures: Theory and Applications",
            "First Author": "Lorenzo Lucchese",
            "Affiliation": "Department of Mathematics, Imperial College London, London, United Kingdom",
            "Personal Website": "https://scholar.google.com/citations?user=-dZCdJoAAAAJ"
        },
        {
            "Title": "AutoML-Agent: A Multi-Agent LLM Framework for Full-Pipeline AutoML",
            "First Author": "Patara Trirat",
            "Affiliation": "DeepAuto.ai",
            "Personal Website": "https://scholar.google.com/citations?user=fDZjV8EAAAAJ"
        },
        {
            "Title": "Learning Smooth and Expressive Interatomic Potentials for Physical Property Prediction",
            "First Author": "Xiang Fu",
            "Affiliation": "Fundamental AI Research (FAIR) at Meta",
            "Personal Website": "https://scholar.google.com/citations?user=Cb-ZgHEAAAAJ"
        },
        {
            "Title": "Multi-agent Architecture Search via Agentic Supernet",
            "First Author": "Guibin Zhang",
            "Affiliation": "National University of Singapore, Tongji University",
            "Personal Website": "https://scholar.google.com/citations?user=ApmxNvwAAAAJ"
        }
    ]
    
    df1 = pd.DataFrame(perfect_data)
    df1.to_excel(base_dir / "test_workspace_1" / "paper_initial.xlsx", index=False)
    print("✓ Created test_workspace_1: Perfect Excel file")
    
    # Test Workspace 2: Missing affiliations (some empty)
    missing_affiliations_data = perfect_data.copy()
    missing_affiliations_data[1]["Affiliation"] = ""  # Empty affiliation
    missing_affiliations_data[3]["Affiliation"] = None  # None affiliation
    
    df2 = pd.DataFrame(missing_affiliations_data)
    df2.to_excel(base_dir / "test_workspace_2" / "paper_initial.xlsx", index=False)
    print("✓ Created test_workspace_2: Missing affiliations")
    
    # Test Workspace 3: Wrong affiliations that contain forbidden items
    wrong_affiliations_data = perfect_data.copy()
    # First paper should NOT contain "Anthropic AI"
    wrong_affiliations_data[0]["Affiliation"] = "Gatsby Computational Neuroscience Unit, University College London, work completed while at the Gatsby Unit, Anthropic AI"
    # Fifth paper should NOT contain "KAIST" 
    wrong_affiliations_data[4]["Affiliation"] = "DeepAuto.ai, KAIST, Seoul, South Korea"
    
    df3 = pd.DataFrame(wrong_affiliations_data)
    df3.to_excel(base_dir / "test_workspace_3" / "paper_initial.xlsx", index=False)
    print("✓ Created test_workspace_3: Wrong affiliations (forbidden content)")
    
    # Test Workspace 4: Missing required affiliation parts
    missing_required_data = perfect_data.copy()
    # First paper missing "University College London"
    missing_required_data[0]["Affiliation"] = "Gatsby Computational Neuroscience Unit"
    # Third paper missing "CREST"
    missing_required_data[2]["Affiliation"] = "ENSAE, IP Paris"
    
    df4 = pd.DataFrame(missing_required_data)
    df4.to_excel(base_dir / "test_workspace_4" / "paper_initial.xlsx", index=False)
    print("✓ Created test_workspace_4: Missing required affiliation parts")
    
    # Test Workspace 5: Wrong structure (missing columns, wrong count)
    wrong_structure_data = [
        {
            "Paper Title": "Strategy Coopetition Explains the Emergence and Transience of In-Context Learning",  # Wrong column name
            "Author": "Aaditya K Singh",  # Wrong column name  
            "Institution": "Gatsby Unit",  # Wrong column name
            "Website": "https://scholar.google.com/citations?user=9OPKqmMAAAAJ"  # Wrong column name
        },
        {
            "Paper Title": "Model Immunization from a Condition Number Perspective",
            "Author": "Amber Yijia Zheng",
            "Institution": "Purdue",
            "Website": "https://scholar.google.com/citations?user=SZQIVG0AAAAJ"
        }
        # Also missing 5 rows (only 2 instead of 7)
    ]
    
    df5 = pd.DataFrame(wrong_structure_data)
    df5.to_excel(base_dir / "test_workspace_5" / "paper_initial.xlsx", index=False)
    print("✓ Created test_workspace_5: Wrong structure")

if __name__ == "__main__":
    create_test_workspaces()
    print("\nAll test workspaces created successfully!")