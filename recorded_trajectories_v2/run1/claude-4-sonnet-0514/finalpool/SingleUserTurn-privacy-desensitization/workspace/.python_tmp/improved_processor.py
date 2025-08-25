import re
import os
from pathlib import Path

class ImprovedPrivacyDesensitizer:
    def __init__(self):
        # More precise regex patterns for sensitive information
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            # More precise IP pattern that requires all 4 octets to be valid IP ranges
            'ip_address': r'\b(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\b'
        }
    
    def desensitize_text(self, text):
        """Desensitize sensitive information in text"""
        desensitized_text = text
        
        # Process each pattern type
        for pattern_type, pattern in self.patterns.items():
            desensitized_text = re.sub(pattern, '***', desensitized_text)
        
        return desensitized_text
    
    def process_file(self, file_path, output_dir):
        """Process a single file and create desensitized copy"""
        try:
            file_path = Path(file_path)
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Desensitize content
            desensitized_content = self.desensitize_text(content)
            
            # Create output filename
            stem = file_path.stem
            suffix = file_path.suffix
            output_filename = f"{stem}_desensitized{suffix}"
            output_path = Path(output_dir) / output_filename
            
            # Write desensitized content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(desensitized_content)
            
            return True, f"Successfully reprocessed {file_path.name} -> {output_filename}"
            
        except Exception as e:
            return False, f"Error processing {file_path.name}: {str(e)}"

# Reprocess all files with improved patterns
workspace_dir = "/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-privacy-desensitization/workspace"
output_dir = os.path.join(workspace_dir, "desensitized_documents")

improved_desensitizer = ImprovedPrivacyDesensitizer()

# Get list of original files to reprocess
input_path = Path(workspace_dir)
files_to_process = []

for file_path in input_path.iterdir():
    if (file_path.is_file() and 
        not file_path.name.startswith('.') and 
        file_path.name not in ['privacy_desensitizer.py', 'process_all_files.py'] and
        'desensitized' not in file_path.name):
        files_to_process.append(file_path)

print(f"Reprocessing {len(files_to_process)} files with improved patterns...")

results = []
for file_path in files_to_process:
    success, message = improved_desensitizer.process_file(file_path, output_dir)
    results.append((file_path.name, success, message))

print("\nImproved Privacy Desensitization Results:")
print("=" * 50)

success_count = 0
error_count = 0

for filename, success, message in results:
    if success:
        success_count += 1
        print(f"✓ {message}")
    else:
        error_count += 1
        print(f"✗ {message}")

print(f"\nFinal Summary:")
print(f"Successfully processed: {success_count} files")
print(f"Errors: {error_count} files")