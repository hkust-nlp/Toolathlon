Analyze the GitHub repository https://github.com/atom/atom. Among all its **stable releases** (exclude pre-releases and drafts), find the release whose attached assets have the largest total size in bytes. Then, within that release, find the single largest asset. Save the results to a CSV file named `heaviest_release.csv` in the workspace, with exactly one data row and the following columns:

- `heaviest_release_tag`: the tag name of the stable release with the largest total asset size
- `total_assets_size`: the total size in bytes of all assets attached to that release (integer)
- `largest_asset_name`: the file name of the single largest asset in that release
- `largest_asset_size`: the size in bytes of that asset (integer)
