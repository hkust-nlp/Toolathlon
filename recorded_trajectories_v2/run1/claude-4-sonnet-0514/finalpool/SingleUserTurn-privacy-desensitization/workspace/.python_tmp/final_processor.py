import re
import os
from pathlib import Path

class FinalPrivacyDesensitizer:
    def __init__(self):
        # Most precise regex patterns for sensitive information
        self.patterns = [
            # Email addresses - process first to avoid conflicts
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'),
            
            # SSN in XXX-XX-XXXX format
            (r'\b\d{3}-\d{2}-\d{4}\b', 'ssn'),
            
            # Credit card numbers (16 digits with optional separators)
            (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', 'credit_card'),
            
            # US Phone numbers - various formats
            (r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b', 'phone'),
            
            # IP addresses - very precise pattern
            (r'\b(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\b', 'ip_address'),
        ]
    
    def desensitize_text(self, text):
        """Desensitize sensitive information in text"""
        desensitized_text = text
        
        # Process each pattern in order
        for pattern, pattern_type in self.patterns:
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
            
            return True, f"Final processing: {file_path.name} -> {output_filename}"
            
        except Exception as e:
            return False, f"Error processing {file_path.name}: {str(e)}"

# Final processing with the most precise patterns
workspace_dir = "/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-privacy-desensitization/workspace"
output_dir = os.path.join(workspace_dir, "desensitized_documents")

final_desensitizer = FinalPrivacyDesensitizer()

# Test with the problematic security log first
test_text = """2024-12-01 09:05:22 [ACCESS] Door opened by user john.smith@company.com, IP: 192.168.1.150
2024-12-01 09:25:06 [CAMERA] Motion detected at Camera-05, IP: 192.168.200.105"""

print("Testing with problematic text:")
print("Original:")
print(test_text)
print("\nDesensitized:")
print(final_desensitizer.desensitize_text(test_text))
print("\n" + "="*50)

# Process all files one final time
input_path = Path(workspace_dir)
files_to_process = []

for file_path in input_path.iterdir():
    if (file_path.is_file() and 
        not file_path.name.startswith('.') and 
        file_path.name not in ['privacy_desensitizer.py', 'process_all_files.py', 'improved_processor.py'] and
        'desensitized' not in file_path.name):
        files_to_process.append(file_path)

print(f"Final processing of {len(files_to_process)} files...")

success_count = 0
for file_path in files_to_process:
    success, message = final_desensitizer.process_file(file_path, output_dir)
    if success:
        success_count += 1

print(f"Final processing complete: {success_count}/{len(files_to_process)} files successfully processed")