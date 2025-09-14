# Copyright 2024 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Offline evaluate the performance of a generated file using reward model and ground truth verifier.
The input is a parquet file that contains N generated sequences and (optional) the ground truth.

"""

import hydra
from verl.utils.fs import copy_local_path_from_hdfs
from verl.utils.reward_score import math
import pandas as pd
import numpy as np

from deepscaler.rewards.math_reward import deepscaler_reward_fn


def select_reward_fn(data_source):
    if data_source == 'lighteval/MATH':
        return math.compute_score
    else:
        return deepscaler_reward_fn


@hydra.main(config_path='config', config_name='evaluation', version_base=None)
def main(config):
    local_path = copy_local_path_from_hdfs(config.data.path)
    dataset = pd.read_parquet(local_path)
    prompts = dataset[config.data.prompt_key]
    responses = dataset[config.data.response_key]
    data_sources = dataset[config.data.data_source_key]
    reward_model_data = dataset[config.data.reward_model_key]

    passes = 0

    total = len(dataset)
    total_scores = []
    for i in range(total):
        response_lst = responses[i]
        data_source = data_sources[i]
        # select reward score based on data_source
        prompt = prompts[i]
        reward_data = reward_model_data[i]
        reward_fn = select_reward_fn(data_source)
        ground_truth = reward_data['ground_truth']
        score_lst = []
        for r in response_lst:
            score = reward_fn(r, ground_truth)
            score_lst.append(score)
        max_score = np.max(score_lst)
        total_scores.append(score_lst)
        n_samples = len(response_lst)
        if max_score == 1:
            passes += 1
    print(f'Pass@1, Avg: {np.mean(total_scores)}')
    print(f'Pass@{n_samples}: {passes / total}')


if __name__ == '__main__':
    main()
