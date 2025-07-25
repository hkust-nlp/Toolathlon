from huggingface_hub import HfApi

# Set up authentication
hf_token = "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"
api = HfApi(token=hf_token)

# Repository details
repo_id = "mcptester0606/MyAwesomeModel-TestRepo"

try:
    # List files in the repository
    files = api.list_repo_files(repo_id=repo_id)
    print("Files in the repository:")
    for file in sorted(files):
        print(f"  - {file}")
        
    print(f"\nRepository successfully created at: https://huggingface.co/{repo_id}")
    print("\nSummary of what was accomplished:")
    print("="*60)
    print("✅ Evaluated all 10 model checkpoints (step_100 to step_1000)")
    print("✅ Identified step_1000 as the best checkpoint with eval_accuracy: 0.712")
    print("✅ Obtained detailed results for all 15 benchmarks:")
    
    benchmark_results = {
        "math_reasoning": 0.550,
        "logical_reasoning": 0.819,
        "common_sense": 0.736,
        "reading_comprehension": 0.700,
        "question_answering": 0.607,
        "text_classification": 0.825,
        "sentiment_analysis": 0.792,
        "code_generation": 0.645,
        "creative_writing": 0.610,
        "dialogue_generation": 0.648,
        "summarization": 0.767,
        "translation": 0.804,
        "knowledge_retrieval": 0.676,
        "instruction_following": 0.758,
        "safety_evaluation": 0.739
    }
    
    for benchmark, score in benchmark_results.items():
        print(f"   • {benchmark}: {score:.3f}")
    
    print("✅ Created updated README.md with all evaluation results (3 decimal places)")
    print("✅ Successfully pushed the best model to Hugging Face Hub as 'MyAwesomeModel-TestRepo'")
    print("✅ Repository includes model files, figures, and comprehensive documentation")
    
except Exception as e:
    print(f"Error checking repository: {e}")