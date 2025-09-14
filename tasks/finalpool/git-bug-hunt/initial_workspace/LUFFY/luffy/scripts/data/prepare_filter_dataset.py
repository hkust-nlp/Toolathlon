"""Script to prepare DeepScaler training and test datasets.

This script processes math problem datasets into a standardized format for training
and testing DeepScaler models. It loads problems from specified datasets, adds
instruction prompts, and saves the processed data as parquet files.
"""

import argparse
import os
from typing import Dict, List, Optional, Any

import pandas as pd
from verl.utils.hdfs_io import copy, makedirs
from verl.utils.reward_score.math import last_boxed_only_string, remove_boxed

from deepscaler.data.utils import load_dataset
from deepscaler.data.dataset_types import TrainDataset, TestDataset


def extract_solution(solution_str: str) -> str:
    """Extract the final boxed solution from a solution string.

    Args:
        solution_str: Raw solution string that may contain multiple boxed answers

    Returns:
        The final boxed answer with box notation removed
    """
    return remove_boxed(last_boxed_only_string(solution_str))


def make_map_fn(split: str):
    """Create a mapping function to process dataset examples.

    Args:
        split: Dataset split name ('train' or 'test')

    Returns:
        Function that processes individual dataset examples
    """
    def process_fn(example: Dict[str, Any], idx: int) -> Optional[Dict[str, Any]]:
        question = example.pop('problem')
        instruction = "Let's think step by step and output the final answer within \\boxed{}."
        question = f"{question} {instruction}"
        answer = example.pop('answer')

        data = {
            "data_source": "",
            "prompt": [{
                "role": "user",
                "content": question
            }],
            "ability": "math",
            "reward_model": {
                "style": "rule",
                "ground_truth": answer
            },
            "extra_info": {
                'split': split,
                'index': idx
            }
        }
        return data
    return process_fn

def make_openr1_map_fn(split: str):
    """Create a mapping function to process dataset examples.

    Args:
        split: Dataset split name ('train' or 'test')

    Returns:
        Function that processes individual dataset examples
    """
    def process_fn(example: Dict[str, Any], idx: int) -> Optional[Dict[str, Any]]:
        question = example.pop('problem')
        # instruction = "Let's think step by step and output the final answer within \\boxed{}."
        # instruction = "Think step by step within <think></think> tags, then generate the final answer within <begin_of_solution></begin_of_solution> tags.  Output the final answer in \\boxed{}."
        # instruction = "Think step by step within <think></think> tags, then generate your answer.  Output the final answer in \\boxed{}."
        instruction = """Your task is to follow a systematic, thorough reasoning process before providing the final solution. This involves analyzing, summarizing, exploring, reassessing, and refining your thought process through multiple iterations. Structure your response into two sections: Thought and Solution. In the Thought section, present your reasoning using the format: "<think>\n {thoughts} </think>\n". Each thought should include detailed analysis, brainstorming, verification, and refinement of ideas. After "</think>\n," in the Solution section, provide the final, logical, and accurate answer, clearly derived from the exploration in the Thought section. If applicable, include the answer in \\boxed{} for closed-form results like multiple choices or mathematical solutions."""
        
        # question = f"{question} {instruction}"
        question = f"{question}"
        answer = example.pop('answer')
        if split == 'train':
            generations = example.pop('generations')
            target = generations[0]
        else:
            target = None
        
        # is_reasoning_complete = example['is_reasoning_complete']
        # correctness_math_verify = example['correctness_math_verify']
        # assert len(correctness_math_verify) == len(is_reasoning_complete)
        # for i in range(len(correctness_math_verify)):
            # if correctness_math_verify[i] == True and is_reasoning_complete[i] == True:
            # break

        if split == 'train':
            data = {
                "data_source": "",
                "prompt": [{
                "role": "system",
                "content": instruction
            },
                {
                "role": "user",
                "content": question
            }],
            'target': [{
                "role": "assistant",
                "content": target
            }],
            "ability": "math",
            "reward_model": {
                "style": "rule",
                "ground_truth": answer
            },
            "extra_info": {
                'split': 'default',
                    'index': idx
                }
            }
        else:
            assert target is None
            data = {
                "data_source": "",
                "prompt": [{
                "role": "system",
                "content": instruction
            },
                {
                "role": "user",
                "content": question
            }],
            "ability": "math",
            "reward_model": {
                "style": "rule",
                "ground_truth": answer
            },
            "extra_info": {
                'split': 'default',
                    'index': idx
                }
            }
        return data
    return process_fn

def filter_function(example):
    is_reasoning_complete = example['is_reasoning_complete']
    correctness_math_verify = example['correctness_math_verify']
    assert len(correctness_math_verify) == len(is_reasoning_complete)
    filter = False
    for i in range(len(correctness_math_verify)):
        if correctness_math_verify[i] == True and is_reasoning_complete[i] == True:
            filter = True
    return filter


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process datasets for DeepScaler training')
    parser.add_argument('--local_dir', default=os.path.expanduser('~/openr1/data'),
                       help='Local directory to save processed datasets')
    parser.add_argument('--hdfs_dir', default=None,
                       help='Optional HDFS directory to copy datasets to')
    args = parser.parse_args()

    local_dir = args.local_dir
    hdfs_dir = args.hdfs_dir
    
    # Make local directory if it doesn't exist
    makedirs(local_dir)

    # Initialize datasets
    # train_datasets = [TrainDataset.DEEPSCALER]
    # train_datasets = [TrainDataset.MATH]
    # train_dataset = load_dataset('open-r1/OpenR1-Math-220k') # 94k
    import datasets
    train_dataset = datasets.load_dataset('open-r1/OpenR1-Math-220k', split='train') # 94k    # filter the dataset
    print('before filter:', len(train_dataset))
    train_dataset = train_dataset.filter(filter_function)
    print('after filter:', len(train_dataset))
    
    test_datasets = [TestDataset.AIME, TestDataset.AMC, TestDataset.MATH, TestDataset.MINERVA, TestDataset.OLYMPIAD_BENCH]
    
    test_datasets_data = [load_dataset(d) for d in test_datasets]

    # Process training data
    train_data: List[Dict[str, Any]] = []
    process_fn = make_openr1_map_fn('train')
    for idx, example in enumerate(train_dataset):
        processed_example = process_fn(example, idx)
        if processed_example is not None:
            train_data.append(processed_example)

    # Process and save each test dataset separately
    for test_dataset, test_data_list in zip(test_datasets, test_datasets_data):
        test_data: List[Dict[str, Any]] = []
        test_process_fn = make_openr1_map_fn('test')
        for idx, example in enumerate(test_data_list):
            processed_example = test_process_fn(example, idx)
            if processed_example is not None:
                test_data.append(processed_example)

        dataset_name = test_dataset.value.lower()
        test_df = pd.DataFrame(test_data)
        test_df.to_parquet(os.path.join(local_dir, f'{dataset_name}.parquet'))
        print(f"{dataset_name} test data size:", len(test_data))

    # Save training dataset
    print("train data size:", len(train_data))
    train_df = pd.DataFrame(train_data)
    train_df.to_parquet(os.path.join(local_dir, 'train.parquet'))

    # Optionally copy to HDFS
    if hdfs_dir is not None:
        makedirs(hdfs_dir)
        copy(src=local_dir, dst=hdfs_dir)