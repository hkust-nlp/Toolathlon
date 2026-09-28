import asyncio
import pandas as pd
from argparse import ArgumentParser
import os

from utils.evaluation.retry import grade_with_retry


def _check_heaviest_release(csv_file_path: str):
    """Read the CSV and validate it matches the expected GitHub release stats.

    Ground truth is frozen: atom/atom has been archived (read-only) since
    2023, so its releases and assets are immutable.
    """
    if not os.path.exists(csv_file_path):
        return False, f"heaviest_release.csv file not found: {csv_file_path}"

    try:
        df = pd.read_csv(csv_file_path)
    except Exception as e:
        return False, f"Could not read CSV file '{csv_file_path}': {e}"

    required_columns = [
        'heaviest_release_tag', 'total_assets_size',
        'largest_asset_name', 'largest_asset_size',
    ]
    if not all(col in df.columns for col in required_columns):
        return False, (
            f"CSV file missing required columns. "
            f"Expected: {required_columns}, Got: {list(df.columns)}"
        )

    if len(df) != 1:
        return False, f"CSV file should contain exactly one row of data. Found {len(df)} rows."

    row = df.iloc[0]
    try:
        actual_tag = str(row['heaviest_release_tag']).strip()
        actual_total = int(row['total_assets_size'])
        actual_asset_name = str(row['largest_asset_name']).strip()
        actual_asset_size = int(row['largest_asset_size'])
    except (ValueError, TypeError) as e:
        return False, f"Could not parse CSV values: {e}"

    expected_tag = "v1.56.0"
    expected_total = 2196067762
    expected_asset_name = "atom-mac.zip"
    expected_asset_size = 212398577

    errors = []
    if actual_tag != expected_tag:
        errors.append(
            f"Release tag mismatch: expected '{expected_tag}', got '{actual_tag}'"
        )
    if actual_total != expected_total:
        errors.append(
            f"Total assets size mismatch: expected {expected_total}, got {actual_total}"
        )
    if actual_asset_name != expected_asset_name:
        errors.append(
            f"Largest asset name mismatch: expected '{expected_asset_name}', got '{actual_asset_name}'"
        )
    if actual_asset_size != expected_asset_size:
        errors.append(
            f"Largest asset size mismatch: expected {expected_asset_size}, got {actual_asset_size}"
        )

    if errors:
        return False, "Evaluation failed: " + "; ".join(errors)
    return True, None


async def main(args):
    # Check if agent_workspace is provided
    if not args.agent_workspace:
        print("Agent workspace path is required")
        exit(1)

    csv_file_path = os.path.join(args.agent_workspace, 'heaviest_release.csv')

    ok, err = grade_with_retry(lambda: _check_heaviest_release(csv_file_path))
    if not ok:
        print(err)
        exit(1)
    else:
        print("Evaluation successful!")

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--groundtruth_workspace", required=False)
    parser.add_argument("--res_log_file", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    asyncio.run(main(args))
