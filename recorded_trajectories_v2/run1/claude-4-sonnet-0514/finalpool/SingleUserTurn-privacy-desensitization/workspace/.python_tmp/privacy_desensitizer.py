import re
import os
import json
import csv
from pathlib import Path

class PrivacyDesensitizer:
    def __init__(self):
        # Define regex patterns for sensitive information
        self.patterns = {
            'phone': [
                # US phone numbers: (123) 456-7890, 123-456-7890, 123.456.7890, 1234567890
                r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                r'\b\d{3}-\d{3}-\d{4}\b',
                r'\b\(\d{3}\)\s?\d{3}-\d{4}\b',
                r'\b\d{3}\.\d{3}\.\d{4}\b',
                r'\b\d{10}\b'
            ],
            'ssn': [
                # SSN: 123-45-6789, 123456789
                r'\b\d{3}-\d{2}-\d{4}\b',
                r'\b\d{9}\b'
            ],
            'email': [
                # Email addresses
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'credit_card': [
                # Credit card numbers (various formats)
                r'\b(?:\d{4}[-\s]?){3}\d{4}\b',  # 1234-5678-9012-3456 or 1234 5678 9012 3456
                r'\b\d{13,19}\b'  # 13-19 digit numbers (common CC range)
            ],
            'ip_address': [
                # IPv4 addresses
                r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
                # IPv6 addresses (simplified)
                r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'
            ]
        }
    
    def is_likely_sensitive_number(self, text, number_match):
        """Additional validation for numbers to avoid false positives"""
        # For SSN-like 9-digit numbers, check context
        if len(number_match.replace('-', '').replace(' ', '')) == 9:
            # Look for SSN-related keywords nearby
            context_window = 50
            start = max(0, number_match.start() - context_window)
            end = min(len(text), number_match.end() + context_window)
            context = text[start:end].lower()
            
            ssn_keywords = ['ssn', 'social security', 'social', 'security number', 'tax id', 'taxpayer']
            if any(keyword in context for keyword in ssn_keywords):
                return True
            
            # If it looks like a date (year between 1900-2100), probably not SSN
            number_str = number_match.group()
            if re.match(r'\b(19|20)\d{2}', number_str):
                return False
                
        return True
    
    def desensitize_text(self, text):
        """Desensitize sensitive information in text"""
        desensitized_text = text
        
        # Process each pattern type
        for pattern_type, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern_type == 'ssn' and len(pattern.replace('\\b', '').replace('\\d', '').replace('-', '').replace('{', '').replace('}', '')) == 0:
                    # Special handling for SSN to avoid false positives
                    matches = list(re.finditer(pattern, desensitized_text))
                    for match in reversed(matches):  # Reverse to maintain indices
                        if self.is_likely_sensitive_number(text, match):
                            desensitized_text = desensitized_text[:match.start()] + '***' + desensitized_text[match.end():]
                else:
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
            
            return True, f"Successfully processed {file_path.name} -> {output_filename}"
            
        except Exception as e:
            return False, f"Error processing {file_path.name}: {str(e)}"
    
    def process_directory(self, input_dir, output_dir):
        """Process all files in a directory"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Create output directory if it doesn't exist
        output_path.mkdir(exist_ok=True)
        
        results = []
        
        # Process all files in the directory
        for file_path in input_path.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                success, message = self.process_file(file_path, output_path)
                results.append((file_path.name, success, message))
        
        return results

# Test the desensitizer
if __name__ == "__main__":
    # Test with some sample text
    test_text = """
    Contact John Doe at john.doe@email.com or call (555) 123-4567.
    His SSN is 123-45-6789 and credit card is 4532-1234-5678-9012.
    Server IP: 192.168.1.1
    """
    
    desensitizer = PrivacyDesensitizer()
    result = desensitizer.desensitize_text(test_text)
    print("Original:")
    print(test_text)
    print("\nDesensitized:")
    print(result)