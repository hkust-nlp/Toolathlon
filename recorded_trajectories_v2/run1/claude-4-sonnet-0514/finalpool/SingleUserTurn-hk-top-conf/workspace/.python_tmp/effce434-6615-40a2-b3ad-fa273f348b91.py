# First, let's analyze the ICML 2024 bibliography to understand its structure
import re

# Read the ICML 2024 bibliography file
with open('/ssddata/junlong/projects/mcpbench_finalpool_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-hk-top-conf/workspace/icml2024_bibliography.bib', 'r', encoding='utf-8') as f:
    bib_content = f.read()

# Print first few entries to understand the structure
print("First 2000 characters of the bibliography:")
print(bib_content[:2000])
print("\n" + "="*50)

# Let's count total number of papers
paper_entries = re.findall(r'@InProceedings{[^}]+}', bib_content, re.DOTALL)
print(f"Total number of papers in ICML 2024: {len(paper_entries)}")