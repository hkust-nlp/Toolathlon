from argparse import ArgumentParser
import os
import shutil
import tarfile

def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True, help="Path to the agent workspace. Must be specified explicitly.")
    parser.add_argument("--launch_time", required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()
    
    # Ensure agent workspace exists
    os.makedirs(args.agent_workspace, exist_ok=True)
    dst_tar_path = os.path.join(args.agent_workspace, "initial_workspace.tar.gz")

    # Extract tar.gz file, stripping the top-level
    # ``initial_workspace_arrange/`` wrapper so files land directly at
    # the agent workspace root.  The wrapper was a packaging convenience
    # inside the tar; the prompt and grader both describe the target
    # tree relative to the workspace root.  Without this strip, agents
    # reasonably interpret "organize files in my workspace" as either
    # (a) moving things out of the wrapper [passes grader] or
    # (b) reorganizing inside the wrapper [fails grader — GT_STRUCTURE
    # is checked at workspace root].  Removing the wrapper eliminates
    # that ambiguity.
    PREFIX = "initial_workspace_arrange/"
    try:
        with tarfile.open(dst_tar_path, 'r:gz') as tar:
            print(f"Extracting to: {args.agent_workspace}")
            members = []
            for m in tar.getmembers():
                if m.name == PREFIX.rstrip('/'):
                    # The wrapper-directory entry itself — skip.
                    continue
                if m.name.startswith(PREFIX):
                    m.name = m.name[len(PREFIX):]
                if m.name:
                    members.append(m)
            # filter='data' guards against absolute paths / symlink
            # escapes (Python 3.14 deprecation also expects an explicit
            # filter).
            tar.extractall(path=args.agent_workspace, members=members, filter='data')
            print(f"Extraction completed ({len(members)} entries; '{PREFIX}' wrapper stripped)")
    except Exception as e:
        print(f"Extraction failed: {e}")
        return
    
    # Remove the original tar.gz file
    try:
        os.remove(dst_tar_path)
        print(f"Removed the original tar file: {dst_tar_path}")
    except Exception as e:
        print(f"Failed to remove tar file: {e}")
    
    print("Preprocessing completed - workspace files are ready.")

if __name__ == "__main__":
    main()
