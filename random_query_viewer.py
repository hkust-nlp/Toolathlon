#!/usr/bin/env python3
import random
from datasets import load_dataset

def main():
    print("Loading MCPToolBench/MCPToolBenchPP dataset...")
    
    try:
        dataset = load_dataset("MCPToolBench/MCPToolBenchPP")
        

        # Get all samples from the dataset
        if 'train' in dataset:
            samples = dataset['train']
        else:
            # If no train split, use the first available split
            split_name = list(dataset.keys())[0]
            samples = dataset[split_name]
            
        print(f"Dataset loaded successfully! Found {len(samples)} samples.")
        print("Press Enter to see a random query, or Ctrl+C to exit.")
        
        while True:
            try:
                input()  # Wait for Enter key
                
                # Get a random sample
                random_sample = samples[random.randint(0, len(samples) - 1)]
                
                # Print the query field
                if 'query' in random_sample:
                    print(f"\nRandom Query:\n{random_sample['query']}\n")
                else:
                    print("No 'query' field found in this sample.")
                    print(f"Available fields: {list(random_sample.keys())}")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
                
    except Exception as e:
        print(f"Error loading dataset: {e}")
        print("Make sure you have the datasets library installed: pip install datasets")

if __name__ == "__main__":
    main()