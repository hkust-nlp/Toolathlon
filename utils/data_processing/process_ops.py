import os
import shutil
import re

def copy_file_with_increment_advanced(source_path, target_dir=None):
    """
    Copy a file with a naming rule like copy, copy 2, copy 3, etc.

    Args:
        source_path: The source file path.
        target_dir: The target directory (optional). If not specified, the file will be copied to the source file's directory.

    Returns:
        str: The path of the newly created file.
    """
    # Check if source file exists
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file does not exist: {source_path}")

    if not os.path.isfile(source_path):
        raise ValueError(f"Path is not a file: {source_path}")

    # Determine target directory
    if target_dir is None:
        target_dir = os.path.dirname(source_path)
    else:
        # Ensure target directory exists
        os.makedirs(target_dir, exist_ok=True)

    # Get filename and extension
    filename = os.path.basename(source_path)
    name, ext = os.path.splitext(filename)

    # Check current filename for "copy" or "copy N" pattern to avoid "test copy copy.txt"
    copy_pattern = r'(.+?)(?: copy(?: (\d+))?)?$'
    match = re.match(copy_pattern, name)
    if match:
        base_name = match.group(1)
    else:
        base_name = name

    # If copying to the same directory, use "copy" suffix directly
    if target_dir == os.path.dirname(source_path):
        new_filename = f"{base_name} copy{ext}"
        new_path = os.path.join(target_dir, new_filename)

        # If "copy" already exists, try "copy 2", "copy 3", etc.
        counter = 2
        while os.path.exists(new_path):
            new_filename = f"{base_name} copy {counter}{ext}"
            new_path = os.path.join(target_dir, new_filename)
            counter += 1
    else:
        # If copying to another directory, first try the original filename
        new_filename = filename
        new_path = os.path.join(target_dir, new_filename)

        # If file exists, add "copy" suffix
        if os.path.exists(new_path):
            new_filename = f"{name} copy{ext}"
            new_path = os.path.join(target_dir, new_filename)

            counter = 2
            while os.path.exists(new_path):
                new_filename = f"{name} copy {counter}{ext}"
                new_path = os.path.join(target_dir, new_filename)
                counter += 1

    # Copy the file
    try:
        shutil.copy2(source_path, new_path)
        return new_path
    except Exception as e:
        raise Exception(f"Error copying file: {str(e)}")

def get_next_copy_name(file_path):
    """
    Get the next available copy filename without actually copying.

    Args:
        file_path: Path to the file.

    Returns:
        str: Next available filename for a copy.
    """
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)

    new_filename = f"{name} copy{ext}"
    new_path = os.path.join(directory, new_filename)

    counter = 2
    while os.path.exists(new_path):
        new_filename = f"{name} copy {counter}{ext}"
        new_path = os.path.join(directory, new_filename)
        counter += 1

    return new_filename

def copy_multiple_times(file_path, times):
    """
    Copy the same file multiple times.

    Args:
        file_path: Path to the file to be copied.
        times: Number of copies to make.

    Returns:
        list: List of all created copy file paths.
    """
    copies = []
    for i in range(times):
        new_path = copy_file_with_increment_advanced(file_path)
        copies.append(new_path)
        print(f"Created copy {i+1}: {os.path.basename(new_path)}")
    return copies