import re
import os
from collections import defaultdict, Counter

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

print("=== LaTeX Paper Citation and Reference Checker ===\n")

# Extract all citation keys from .bib file
bib_keys = set()
bib_pattern = r'@\w+\{([^,\s]+),'
for match in re.finditer(bib_pattern, bib_content):
    bib_keys.add(match.group(1))

print(f"Found {len(bib_keys)} entries in bibliography file:")
for key in sorted(bib_keys):
    print(f"  - {key}")
print()

# Extract all \cite{} commands from LaTeX files
cite_pattern = r'\\cite[tp]?\{([^}]+)\}'
all_citations = []
citation_issues = []

print("=== CITATION ANALYSIS ===")
for filename, content in all_content.items():
    file_citations = []
    for match in re.finditer(cite_pattern, content):
        citation_keys = [key.strip() for key in match.group(1).split(',')]
        for key in citation_keys:
            file_citations.append(key)
            all_citations.append((filename, key))
    
    if file_citations:
        print(f"\n{filename}: {len(file_citations)} citations")
        for key in sorted(set(file_citations)):
            if key not in bib_keys:
                print(f"  ❌ MISSING: {key}")
                citation_issues.append(f"Missing bib entry: {key} (used in {filename})")
            else:
                print(f"  ✅ {key}")

print(f"\n=== CITATION ISSUES SUMMARY ===")
if citation_issues:
    print(f"Found {len(citation_issues)} citation issues:")
    for issue in citation_issues:
        print(f"  - {issue}")
else:
    print("✅ All citations have corresponding bibliography entries!")

# Check for unused bibliography entries
used_citations = set([key for _, key in all_citations])
unused_bib_entries = bib_keys - used_citations

if unused_bib_entries:
    print(f"\n📚 Unused bibliography entries ({len(unused_bib_entries)}):")
    for key in sorted(unused_bib_entries):
        print(f"  - {key}")
else:
    print("\n✅ All bibliography entries are used!")

print(f"\n=== LABEL AND REFERENCE ANALYSIS ===")

# Extract all \label{} commands
label_pattern = r'\\label\{([^}]+)\}'
all_labels = []
labels_by_file = defaultdict(list)

for filename, content in all_content.items():
    for match in re.finditer(label_pattern, content):
        label = match.group(1)
        all_labels.append(label)
        labels_by_file[filename].append(label)

print(f"Found {len(all_labels)} labels:")
for filename, labels in labels_by_file.items():
    if labels:
        print(f"\n{filename}:")
        for label in labels:
            print(f"  - {label}")

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

print(f"\n=== REFERENCE ANALYSIS ===")
for filename, content in all_content.items():
    file_refs = []
    for pattern in ref_patterns:
        for match in re.finditer(pattern, content):
            ref_key = match.group(1)
            file_refs.append(ref_key)
            all_references.append((filename, ref_key, pattern))
    
    if file_refs:
        print(f"\n{filename}: {len(file_refs)} references")
        for ref_key in sorted(set(file_refs)):
            if ref_key not in all_labels:
                print(f"  ❌ MISSING LABEL: {ref_key}")
                reference_issues.append(f"Missing label: {ref_key} (referenced in {filename})")
            else:
                print(f"  ✅ {ref_key}")

print(f"\n=== REFERENCE ISSUES SUMMARY ===")
if reference_issues:
    print(f"Found {len(reference_issues)} reference issues:")
    for issue in reference_issues:
        print(f"  - {issue}")
else:
    print("✅ All references have corresponding labels!")

# Check for unused labels
used_references = set([ref for _, ref, _ in all_references])
unused_labels = set(all_labels) - used_references

if unused_labels:
    print(f"\n🏷️  Unused labels ({len(unused_labels)}):")
    for label in sorted(unused_labels):
        print(f"  - {label}")
else:
    print("\n✅ All labels are referenced!")

print(f"\n=== OVERALL SUMMARY ===")
print(f"📊 Statistics:")
print(f"  - Bibliography entries: {len(bib_keys)}")
print(f"  - Citations used: {len(used_citations)}")
print(f"  - Labels defined: {len(all_labels)}")
print(f"  - References made: {len(set(used_references))}")
print(f"  - Citation issues: {len(citation_issues)}")
print(f"  - Reference issues: {len(reference_issues)}")

if citation_issues or reference_issues:
    print(f"\n❌ Found {len(citation_issues) + len(reference_issues)} total issues that need fixing!")
else:
    print(f"\n✅ No citation or reference issues found! Your LaTeX paper is well-structured.")