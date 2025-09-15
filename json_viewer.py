#!/usr/bin/env python3
"""
JSON/JSONL File Viewer - A Streamlit app for viewing JSON and JSONL files
"""

import streamlit as st
import json
import os
from pathlib import Path
import traceback

# Configure the Streamlit page
st.set_page_config(
    page_title="JSON/JSONL File Viewer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def is_valid_json_line(line):
    """Check if a line is valid JSON"""
    line = line.strip()
    if not line:
        return False
    try:
        json.loads(line)
        return True
    except (json.JSONDecodeError, ValueError):
        return False

def load_json_file(file_path):
    """Load a single JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading JSON file: {e}")
        return None

def load_jsonl_file(file_path):
    """Load a JSONL file and return valid JSON lines"""
    valid_lines = []
    invalid_count = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                if is_valid_json_line(line):
                    try:
                        json_obj = json.loads(line)
                        valid_lines.append({
                            'line_number': line_num,
                            'data': json_obj
                        })
                    except Exception as e:
                        invalid_count += 1
                else:
                    invalid_count += 1

        return valid_lines, invalid_count
    except Exception as e:
        st.error(f"Error loading JSONL file: {e}")
        return [], 0

def display_json(json_data, title="JSON Data"):
    """Display JSON data in a formatted way"""
    st.subheader(title)

    # Show as JSON (this is the cleaner, easier to read format)
    st.json(json_data)

def main():
    st.title("📄 JSON/JSONL File Viewer")
    st.markdown("View JSON and JSONL files with an easy-to-read web interface")

    # Sidebar for file input
    with st.sidebar:
        st.header("File Selection")

        # File path input
        file_path = st.text_input(
            "Enter absolute file path:",
            placeholder="/path/to/your/file.json",
            help="Enter the full absolute path to a JSON or JSONL file"
        )

        # Quick navigation for common directories
        st.subheader("Quick Navigation")
        if st.button("📁 Browse dumps_0913_all_gpt5mini"):
            st.session_state['browse_dir'] = "/mnt/mcpbench-jh/dumps_0913_all_gpt5mini"

        if 'browse_dir' in st.session_state:
            browse_dir = st.session_state['browse_dir']
            if os.path.exists(browse_dir):
                st.write(f"**Current directory:** {browse_dir}")

                # List files in directory
                try:
                    files = []
                    for item in os.listdir(browse_dir):
                        item_path = os.path.join(browse_dir, item)
                        if os.path.isfile(item_path) and (item.endswith('.json') or item.endswith('.jsonl')):
                            files.append(item)

                    if files:
                        selected_file = st.selectbox("Select a file:", [""] + sorted(files))
                        if selected_file:
                            file_path = os.path.join(browse_dir, selected_file)
                            st.session_state['selected_file_path'] = file_path
                    else:
                        st.info("No JSON/JSONL files found in this directory")

                        # Show subdirectories
                        subdirs = [item for item in os.listdir(browse_dir)
                                 if os.path.isdir(os.path.join(browse_dir, item))]
                        if subdirs:
                            st.write("**Subdirectories:**")
                            for subdir in sorted(subdirs)[:10]:  # Limit to first 10
                                subdir_path = os.path.join(browse_dir, subdir)
                                if st.button(f"📁 {subdir}"):
                                    st.session_state['browse_dir'] = subdir_path
                                    st.rerun()

                except Exception as e:
                    st.error(f"Error browsing directory: {e}")

    # Use selected file path if available
    if 'selected_file_path' in st.session_state:
        file_path = st.session_state['selected_file_path']

    # Main content area
    if not file_path:
        st.info("👆 Please enter a file path in the sidebar to get started")
        st.markdown("""
        ### How to use:
        1. Enter the absolute path to a JSON or JSONL file in the sidebar
        2. For JSON files: The content will be displayed in a formatted way
        3. For JSONL files: Navigate through pages to view each JSON object
        4. Use the quick navigation to browse common directories

        ### Examples:
        - `/mnt/mcpbench-jh/dumps_0913_all_gpt5mini/traj_log_all.jsonl`
        - `/mnt/mcpbench-jh/dumps_0913_all_gpt5mini/finalpool/gdp-cr5-analysis/traj_log.json`
        """)
        return

    # Validate file path
    if not os.path.exists(file_path):
        st.error(f"❌ File not found: {file_path}")
        return

    if not os.path.isfile(file_path):
        st.error(f"❌ Path is not a file: {file_path}")
        return

    # Display file info
    file_info = os.stat(file_path)
    file_size = file_info.st_size
    file_size_mb = file_size / (1024 * 1024)

    st.success(f"✅ File found: {file_path}")
    st.info(f"📊 File size: {file_size_mb:.2f} MB ({file_size:,} bytes)")

    # Determine file type and process accordingly
    file_extension = Path(file_path).suffix.lower()

    if file_extension == '.json':
        st.header("📄 JSON File")
        json_data = load_json_file(file_path)
        if json_data is not None:
            display_json(json_data, "JSON Content")

    elif file_extension == '.jsonl':
        st.header("📄 JSONL File")

        with st.spinner("Loading JSONL file..."):
            valid_lines, invalid_count = load_jsonl_file(file_path)

        if not valid_lines:
            st.warning("No valid JSON lines found in the file")
            return

        total_valid = len(valid_lines)
        st.success(f"✅ Found {total_valid} valid JSON objects")

        if invalid_count > 0:
            st.warning(f"⚠️ Skipped {invalid_count} invalid lines")

        # Pagination for JSONL
        if total_valid > 0:
            # Items per page
            items_per_page = st.selectbox(
                "Items per page:",
                [1, 5, 10, 20, 50],
                index=0,
                key="items_per_page"
            )

            total_pages = (total_valid + items_per_page - 1) // items_per_page

            # Page navigation
            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                if st.button("⬅️ Previous", disabled=st.session_state.get('current_page', 1) <= 1):
                    st.session_state['current_page'] = max(1, st.session_state.get('current_page', 1) - 1)
                    st.rerun()

            with col2:
                current_page = st.number_input(
                    f"Page (1-{total_pages}):",
                    min_value=1,
                    max_value=total_pages,
                    value=st.session_state.get('current_page', 1),
                    key="page_input"
                )
                st.session_state['current_page'] = current_page

            with col3:
                if st.button("➡️ Next", disabled=st.session_state.get('current_page', 1) >= total_pages):
                    st.session_state['current_page'] = min(total_pages, st.session_state.get('current_page', 1) + 1)
                    st.rerun()

            # Calculate page range
            start_idx = (current_page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, total_valid)

            st.markdown(f"**Showing items {start_idx + 1}-{end_idx} of {total_valid}**")

            # Display items for current page
            for i in range(start_idx, end_idx):
                line_data = valid_lines[i]

                with st.expander(f"Line {line_data['line_number']} (Item {i + 1})", expanded=(items_per_page == 1)):
                    display_json(line_data['data'], f"JSON Object from Line {line_data['line_number']}")

    else:
        st.error(f"❌ Unsupported file type: {file_extension}. Only .json and .jsonl files are supported.")

if __name__ == "__main__":
    # Initialize session state
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 1

    main()

# To run this app, use:
# streamlit run json_viewer.py --server.port 8734 --server.address 0.0.0.0