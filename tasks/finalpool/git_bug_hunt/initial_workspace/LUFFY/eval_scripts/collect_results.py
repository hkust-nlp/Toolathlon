import os
import re
import pandas as pd
from openpyxl import Workbook

def extract_results_from_files(directory_path):
    # Dictionary to store results
    results = {}
    
    # List of benchmark names based on your example
    benchmarks = ['math', 'olympiad_bench', 'minerva', 'aime', 'amc']
    
    # Iterate through all files in the directory
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        
        # Only process files (not directories)
        if os.path.isfile(file_path) and filename.endswith('.log'):
            try:
                with open(file_path, 'r') as file:
                    # Read all lines and take the last 5
                    lines = file.readlines()
                    last_five_lines = lines[-6:]
                    
                    # Create a dictionary for this file's results
                    file_results = {}
                    
                    # Extract benchmark names and scores
                    for line in last_five_lines:
                        # Use regex to extract benchmark name and score
                        match = re.search(r'(\w+):\s+([\d.]+)', line)
                        if match:
                            benchmark_name = match.group(1)
                            score = float(match.group(2))
                            file_results[benchmark_name] = score
                    
                    # Only add to results if we found all expected benchmarks
                    # if all(benchmark in file_results for benchmark in benchmarks):
                    results[filename] = file_results
                    
            except Exception as e:
                print(f"Error processing file {filename}: {e}")
    
    return results

def create_excel_from_results(results, output_file_path):
    # Create a pandas DataFrame from the results
    data = []
    
    for filename, benchmarks in results.items():
        row = {'Filename': filename}
        row.update(benchmarks)
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Move Filename column to the first position if it's not already
    if 'Filename' in df.columns:
        cols = ['Filename'] + [col for col in df.columns if col != 'Filename']
        df = df[cols]
    
    # Write DataFrame to Excel
    df.to_excel(output_file_path, index=False)
    print(f"Results saved to {output_file_path}")

def main(directory_path, output_file_path=None):
    # Ask for the directory path
    # directory_path = input("Enter the directory path containing the files: ")
    
    # Check if directory exists
    if not os.path.isdir(directory_path):
        print(f"Directory '{directory_path}' does not exist.")
        return
    
    # Extract results from files
    results = extract_results_from_files(directory_path)
    
    if not results:
        print("No valid results found in the specified directory.")
        return
    
    # Default output file name
    if output_file_path is None:
        output_file_path = os.path.join(directory_path, "benchmark_results.xlsx")
    
    # Create Excel file
    create_excel_from_results(results, output_file_path)

if __name__ == "__main__":
    import fire
    fire.Fire(main)