#!/usr/bin/env python3
"""
End-to-end test for excel-data-transformation evaluation
Creates one perfect test case and runs the complete evaluation pipeline
"""

import sys
import subprocess
from pathlib import Path
import pandas as pd
import shutil

def create_perfect_test_workspace():
    """Create one perfect test workspace that should pass evaluation"""
    
    base_dir = Path(__file__).parent
    groundtruth_file = base_dir.parent / "groundtruth_workspace" / "Processed.xlsx"
    
    # Create perfect test workspace
    perfect_workspace = base_dir / "perfect_workspace"
    perfect_workspace.mkdir(exist_ok=True)
    
    # Copy ground truth as perfect result
    if groundtruth_file.exists():
        shutil.copy2(groundtruth_file, perfect_workspace / "Processed.xlsx")
        print("✅ Created perfect test workspace with ground truth data")
        return str(perfect_workspace)
    else:
        print(f"❌ Ground truth file not found: {groundtruth_file}")
        return None

def run_end_to_end_test():
    """Run complete end-to-end evaluation test"""
    
    print("🚀 Excel Data Transformation - End-to-End Test")
    print("=" * 60)
    
    # Create perfect test workspace
    perfect_workspace = create_perfect_test_workspace()
    if not perfect_workspace:
        print("❌ Failed to create test workspace")
        return False
    
    # Run evaluation
    base_dir = Path(__file__).parent
    evaluation_script = base_dir.parent / "evaluation" / "main.py"
    groundtruth_workspace = base_dir.parent / "groundtruth_workspace"
    
    print("\n🧪 Running evaluation on perfect workspace...")
    
    cmd = [
        sys.executable,
        str(evaluation_script),
        "--agent_workspace", perfect_workspace,
        "--groundtruth_workspace", str(groundtruth_workspace),
        "--numerical_tolerance", "1e-6"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        print("--- Evaluation Output ---")
        print(result.stdout)
        if result.stderr:
            print("--- Errors ---")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n✅ END-TO-END TEST PASSED")
            print("Perfect workspace correctly passed evaluation")
            return True
        else:
            print(f"\n❌ END-TO-END TEST FAILED")
            print(f"Perfect workspace unexpectedly failed evaluation")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n❌ END-TO-END TEST TIMEOUT")
        return False
    except Exception as e:
        print(f"\n❌ END-TO-END TEST ERROR: {e}")
        return False

if __name__ == "__main__":
    success = run_end_to_end_test()
    sys.exit(0 if success else 1)