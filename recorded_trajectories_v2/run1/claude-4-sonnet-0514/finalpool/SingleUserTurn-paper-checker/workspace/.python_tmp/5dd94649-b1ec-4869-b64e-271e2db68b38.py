import re
import os
from collections import defaultdict

# Read all the LaTeX files
def read_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return ""

# Define file paths
base_path = "/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-paper-checker/workspace/my_paper"

files_to_check = [
    f"{base_path}/colm2024_conference.tex",
    f"{base_path}/sections/1_introduction.tex",
    f"{base_path}/sections/2_scenarios.tex", 
    f"{base_path}/sections/3_advanced.tex",
    f"{base_path}/sections/4_evaluation.tex",
    f"{base_path}/sections/5_tradeoff.tex",
    f"{base_path}/sections/conclusion.tex",
    f"{base_path}/appendix/learning-effort.tex",
    f"{base_path}/appendix/embodied.tex",
    f"{base_path}/math_commands.tex"
]

bib_file = f"{base_path}/colm2024_conference.bib"

# Read all files
all_content = {}
for file_path in files_to_check:
    filename = os.path.basename(file_path)
    all_content[filename] = read_file(file_path)

bib_content = read_file(bib_file)

# Extract all citation keys from .bib file
bib_keys = set()
bib_pattern = r'@\w+\{([^,\s]+),'
for match in re.finditer(bib_pattern, bib_content):
    bib_keys.add(match.group(1))

# Extract all \cite{} commands from LaTeX files
cite_pattern = r'\\cite[tp]?\{([^}]+)\}'
all_citations = []
citation_issues = []

for filename, content in all_content.items():
    for match in re.finditer(cite_pattern, content):
        citation_keys = [key.strip() for key in match.group(1).split(',')]
        for key in citation_keys:
            all_citations.append((filename, key))
            if key not in bib_keys:
                citation_issues.append(f"Missing bib entry: {key} (used in {filename})")

# Extract all \label{} commands
label_pattern = r'\\label\{([^}]+)\}'
all_labels = []

for filename, content in all_content.items():
    for match in re.finditer(label_pattern, content):
        label = match.group(1)
        all_labels.append(label)

# Extract all \ref{}, \autoref{}, and custom ref commands
ref_patterns = [
    r'\\ref\{([^}]+)\}',
    r'\\autoref\{([^}]+)\}',
    r'\\figref\{([^}]+)\}',
    r'\\Figref\{([^}]+)\}',
    r'\\secref\{([^}]+)\}',
    r'\\Secref\{([^}]+)\}',
    r'\\eqref\{([^}]+)\}',
    r'\\Eqref\{([^}]+)\}'
]

all_references = []
reference_issues = []

for filename, content in all_content.items():
    for pattern in ref_patterns:
        for match in re.finditer(pattern, content):
            ref_key = match.group(1)
            all_references.append((filename, ref_key, pattern))
            # Skip macro parameter references like #1, #2, etc.
            if not ref_key.startswith('#') and ref_key not in all_labels:
                reference_issues.append(f"Missing label: {ref_key} (referenced in {filename})")

print("=== FIXED ISSUES VERIFICATION ===")
print(f"Citation issues: {len(citation_issues)}")
print(f"Reference issues: {len(reference_issues)}")

if citation_issues:
    print("\nRemaining citation issues:")
    for issue in citation_issues:
        print(f"  - {issue}")

if reference_issues:
    print("\nRemaining reference issues:")
    for issue in reference_issues:
        print(f"  - {issue}")

if not citation_issues and not reference_issues:
    print("\n✅ All citation and reference issues have been fixed!")
    print("\n=== FINAL SUMMARY ===")
    print(f"✅ All {len(set([key for _, key in all_citations]))} citations have corresponding bibliography entries")
    print(f"✅ All {len(set([ref for _, ref, _ in all_references if not ref.startswith('#')]))} references have corresponding labels")
    print(f"📊 Bibliography entries: {len(bib_keys)}")
    print(f"📊 Labels defined: {len(all_labels)}")
    
    # Check for any other potential issues
    unused_bib = bib_keys - set([key for _, key in all_citations])
    unused_labels = set(all_labels) - set([ref for _, ref, _ in all_references if not ref.startswith('#')])
    
    if unused_bib:
        print(f"\n📚 Note: {len(unused_bib)} bibliography entries are unused (this is often normal)")
    if unused_labels:
        print(f"🏷️  Note: {len(unused_labels)} labels are unused (this is often normal)")