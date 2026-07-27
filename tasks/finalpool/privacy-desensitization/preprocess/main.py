from argparse import ArgumentParser
import os
import shutil
import json
import tarfile
import glob
import tempfile


def is_macos_metadata(path):
    parts = path.replace("\\", "/").split("/")
    return any(part == "__MACOSX" or part == ".DS_Store" or part.startswith("._") for part in parts)


def move_visible_contents(src_dir, dst_dir):
    for name in sorted(os.listdir(src_dir)):
        if is_macos_metadata(name):
            continue
        src = os.path.join(src_dir, name)
        dst = os.path.join(dst_dir, name)
        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        shutil.move(src, dst)


def find_document_root(extract_dir):
    visible = [name for name in os.listdir(extract_dir) if not is_macos_metadata(name)]
    if visible == ["files"] and os.path.isdir(os.path.join(extract_dir, "files")):
        return os.path.join(extract_dir, "files")
    return extract_dir

def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True, help="Path to agent workspace, must be specified explicitly")
    parser.add_argument("--launch_time", required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()
    
    # Ensure agent workspace exists
    os.makedirs(args.agent_workspace, exist_ok=True)
    
    dst_tar_path = os.path.join(args.agent_workspace, "files.tar.gz")
    
    # Extract tar.gz file. Some archives are wrapped in a top-level files/
    # directory; expose documents at the workspace root either way.
    extract_tmp_dir = tempfile.mkdtemp(prefix=".files_extract_", dir=args.agent_workspace)
    try:
        with tarfile.open(dst_tar_path, 'r:gz') as tar:
            print(f"Extracting to temporary directory: {extract_tmp_dir}")
            tar.extractall(path=extract_tmp_dir, filter="data")
            source_dir = find_document_root(extract_tmp_dir)
            move_visible_contents(source_dir, args.agent_workspace)
            print("Extraction completed")
    except Exception as e:
        print(f"Extraction failed: {e}")
        return
    finally:
        if os.path.exists(extract_tmp_dir):
            shutil.rmtree(extract_tmp_dir)
    
    # Delete the tar.gz file
    try:
        os.remove(dst_tar_path)
        print(f"Deleted original archive: {dst_tar_path}")
    except Exception as e:
        print(f"Failed to delete archive: {e}")
    
    # Create desensitized_documents directory (for saving desensitized files)
    desen_docs_dir = os.path.join(args.agent_workspace, "desensitized_documents")
    os.makedirs(desen_docs_dir, exist_ok=True)
    print(f"Created desensitized_documents directory: {desen_docs_dir}")
    
    print("Preprocessing completed")

if __name__ == "__main__":
    main() 