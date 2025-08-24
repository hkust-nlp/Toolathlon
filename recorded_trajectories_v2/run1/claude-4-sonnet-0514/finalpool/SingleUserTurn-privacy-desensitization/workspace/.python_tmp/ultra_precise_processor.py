import re
import os
from pathlib import Path

class UltraPreciseDesensitizer:
    def __init__(self):
        # Ultra-precise patterns with proper word boundaries and validation
        pass
    
    def desensitize_text(self, text):
        """Desensitize sensitive information in text with ultra-precise matching"""
        desensitized_text = text
        
        # 1. Email addresses - most specific first
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        desensitized_text = re.sub(email_pattern, '***', desensitized_text)
        
        # 2. SSN in XXX-XX-XXXX format
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        desensitized_text = re.sub(ssn_pattern, '***', desensitized_text)
        
        # 3. Credit card numbers (exactly 16 digits with separators)
        cc_pattern = r'\b(?:\d{4}[-\s]){3}\d{4}\b'
        desensitized_text = re.sub(cc_pattern, '***', desensitized_text)
        
        # 4. Long credit card numbers without separators (13-19 digits, but not timestamps/years)
        long_cc_pattern = r'\b(?!(?:19|20)\d{2})\d{13,19}\b'
        desensitized_text = re.sub(long_cc_pattern, '***', desensitized_text)
        
        # 5. Phone numbers - US format with various separators
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        desensitized_text = re.sub(phone_pattern, '***', desensitized_text)
        
        # 6. IP addresses - very precise (avoid matching dates/times)
        ip_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\b'
        desensitized_text = re.sub(ip_pattern, '***', desensitized_text)
        
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
            
            return True, f"Ultra-precise processing: {file_path.name} -> {output_filename}"
            
        except Exception as e:
            return False, f"Error processing {file_path.name}: {str(e)}"

# Test with sample data first
test_cases = [
    "Email: john.doe@example.com",
    "Phone: (555) 123-4567",
    "SSN: 123-45-6789", 
    "Credit Card: 4111-1111-1111-1111",
    "Long CC: 1234567890123456",
    "IP: 192.168.1.1",
    "Date: 2024-12-01 (should not be changed)",
    "Time: 09:30:17 (should not be changed)",
    "Year: 2024 (should not be changed)"
]

desensitizer = UltraPreciseDesensitizer()

print("Testing ultra-precise desensitizer:")
for test in test_cases:
    result = desensitizer.desensitize_text(test)
    print(f"'{test}' -> '{result}'")

print("\n" + "="*50)

# Process all files with ultra-precise desensitizer
workspace_dir = "/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-privacy-desensitization/workspace"
output_dir = os.path.join(workspace_dir, "desensitized_documents")

input_path = Path(workspace_dir)
files_to_process = []

for file_path in input_path.iterdir():
    if (file_path.is_file() and 
        not file_path.name.startswith('.') and 
        '.py' not in file_path.name and
        'desensitized' not in file_path.name):
        files_to_process.append(file_path)

print(f"Ultra-precise processing of {len(files_to_process)} files...")

success_count = 0
for file_path in files_to_process:
    success, message = desensitizer.process_file(file_path, output_dir)
    if success:
        success_count += 1

print(f"Ultra-precise processing complete: {success_count}/{len(files_to_process)} files successfully processed")