#!/usr/bin/env python3
import os
import shutil
from pathlib import Path

def rename_files_and_dirs(base_path):
    """
    Rename files and directories according to the specified rules:
    Only perform renaming when both en and non-en versions exist:
    1. For preprocess/ and evaluation/ dirs: main.py -> main_cn.py, main_en.py -> main.py (only if both exist)
    2. For workspace dirs: groundtruth_workspace -> groundtruth_workspace_cn, groundtruth_workspace_en -> groundtruth_workspace (only if both exist)
    3. For docs/ md files: files without _en suffix get _cn suffix, files with _en suffix remove _en suffix (only if both versions exist)
    """
    changes_made = []
    base_path = Path(base_path)
    
    # Find all task directories
    for task_dir in base_path.iterdir():
        if not task_dir.is_dir():
            continue
            
        print(f"Processing task directory: {task_dir.name}")
        
        # Handle preprocess/ and evaluation/ directories
        for subdir_name in ['preprocess', 'evaluation']:
            subdir = task_dir / subdir_name
            if subdir.exists():
                main_py = subdir / 'main.py'
                main_en_py = subdir / 'main_en.py'
                main_cn_py = subdir / 'main_cn.py'
                
                # Only proceed if both main.py and main_en.py exist
                if main_py.exists() and main_en_py.exists():
                    # Create temporary file to avoid conflicts
                    temp_file = subdir / 'temp_main.py'
                    
                    # main.py -> main_cn.py
                    shutil.move(str(main_py), str(temp_file))
                    shutil.move(str(temp_file), str(main_cn_py))
                    changes_made.append(f"{main_py} -> {main_cn_py}")
                    
                    # main_en.py -> main.py
                    shutil.move(str(main_en_py), str(main_py))
                    changes_made.append(f"{main_en_py} -> {main_py}")
        
        # Handle workspace directories
        for workspace_type in ['groundtruth_workspace', 'initial_workspace']:
            workspace = task_dir / workspace_type
            workspace_en = task_dir / f'{workspace_type}_en'
            
            # Only proceed if both directories exist
            if workspace.exists() and workspace_en.exists():
                temp_dir = task_dir / f'temp_{workspace_type}'
                
                # workspace -> workspace_cn (via temp)
                shutil.move(str(workspace), str(temp_dir))
                shutil.move(str(temp_dir), task_dir / f'{workspace_type}_cn')
                changes_made.append(f"{workspace} -> {workspace_type}_cn")
                
                # workspace_en -> workspace
                shutil.move(str(workspace_en), str(workspace))
                changes_made.append(f"{workspace_en} -> {workspace}")
        
        # Handle docs/ directory markdown files
        docs_dir = task_dir / 'docs'
        if docs_dir.exists():
            # Find all markdown files
            md_files = list(docs_dir.glob('*.md'))
            
            # Group files by base name
            file_pairs = {}
            for md_file in md_files:
                name = md_file.stem
                if name.endswith('_en'):
                    base_name = name[:-3]  # Remove _en suffix
                    if base_name not in file_pairs:
                        file_pairs[base_name] = {}
                    file_pairs[base_name]['en'] = md_file
                else:
                    if name not in file_pairs:
                        file_pairs[name] = {}
                    file_pairs[name]['base'] = md_file
            
            # Process pairs where both files exist
            for base_name, files in file_pairs.items():
                if 'base' in files and 'en' in files:
                    base_file = files['base']
                    en_file = files['en']
                    temp_file = docs_dir / f'temp_{base_name}.md'
                    
                    # base_file -> base_name_cn.md
                    shutil.move(str(base_file), str(temp_file))
                    shutil.move(str(temp_file), docs_dir / f'{base_name}_cn.md')
                    changes_made.append(f"{base_file.name} -> {base_name}_cn.md")
                    
                    # en_file -> base_name.md
                    shutil.move(str(en_file), str(base_file))
                    changes_made.append(f"{en_file.name} -> {base_name}.md")
    
    return changes_made

if __name__ == "__main__":
    base_path = "tasks/finalpoolcn"
    
    if not os.path.exists(base_path):
        print(f"Error: Directory {base_path} does not exist")
        exit(1)
    
    print(f"Starting renaming process in {base_path}")
    changes = rename_files_and_dirs(base_path)
    
    print("\n=== SUMMARY OF CHANGES ===")
    if changes:
        for change in changes:
            print(f"  {change}")
        print(f"\nTotal changes made: {len(changes)}")
    else:
        print("No changes were made - no matching file/directory pairs found")
    
    print("Renaming process completed!")