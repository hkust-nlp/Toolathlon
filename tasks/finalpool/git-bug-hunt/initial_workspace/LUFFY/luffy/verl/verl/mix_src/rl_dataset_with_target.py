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

from omegaconf import ListConfig
import os
from typing import List, Union

import pandas as pd
import copy 

import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, PreTrainedTokenizer
from verl.utils.fs import copy_local_path_from_hdfs

from verl.utils.model import compute_position_id_with_mask
import verl.utils.torch_functional as verl_F
from verl.utils.torch_functional import pad_sequence_to_length


import logging
import os
logger = logging.getLogger(__file__)
logger.setLevel(os.getenv('VERL_PPO_LOGGING_LEVEL', 'INFO'))


def collate_fn(data_list: list[dict]) -> dict:
    tensors = {}
    non_tensors = {}

    for data in data_list:
        for key, val in data.items():
            if isinstance(val, torch.Tensor):
                if key not in tensors:
                    tensors[key] = []
                tensors[key].append(val)
            else:
                if key not in non_tensors:
                    non_tensors[key] = []
                non_tensors[key].append(val)

    for key, val in tensors.items():
        tensors[key] = torch.stack(val, dim=0)

    for key, val in non_tensors.items():
        non_tensors[key] = np.array(val, dtype=object)

    output = {}
    output.update(tensors)
    output.update(non_tensors)
    return output

from verl.utils.dataset.rl_dataset import RLHFDataset

class RLHFDatasetWithTarget(RLHFDataset):
    """
    We assume the dataset contains a column that contains prompts and other information
    """

    def __init__(self,
                 parquet_files: Union[str, List[str]],
                 tokenizer: PreTrainedTokenizer,
                 prompt_key='prompt',
                 max_prompt_length=1024,
                 filter_prompts=True,
                 cache_dir='~/.cache/verl/rlhf',
                 chat_template_func=None,
                 return_raw_chat=False,
                 truncation='error',
                 target_key='target',
                 max_target_length=8192,
                 filter_targets=False,
                 sample_target_ratio=1.0,
                 target_list_key='target_lst',
                 max_num_targets=5,
                 target_probs_key='target_ds_qwen_7b_probs',
        ):
        super().__init__(parquet_files, tokenizer, prompt_key, max_prompt_length, filter_prompts, cache_dir, chat_template_func, return_raw_chat, truncation)
        
        self.max_target_length = max_target_length
        self.filter_targets = filter_targets
        self.target_key = target_key
        self.sample_target_ratio = sample_target_ratio
        self.target_list_key = target_list_key
        self.target_probs_key = target_probs_key
        self.max_num_targets = max_num_targets

    def __getitem__(self, item):
        """
        Note that we also return the raw_input_ids so that it can be combined with other chat template
        """
        row_dict = self.dataframe.iloc[item].to_dict()

        chat = row_dict.pop(self.prompt_key)

        prompt_with_chat_template = self.tokenizer.apply_chat_template(chat, add_generation_prompt=True, tokenize=False)

        input_ids, attention_mask = verl_F.tokenize_and_postprocess_data(prompt=prompt_with_chat_template,
                                                                         tokenizer=self.tokenizer,
                                                                         max_length=self.max_prompt_length,
                                                                         pad_token_id=self.tokenizer.pad_token_id,
                                                                         left_pad=True,
                                                                         truncation=self.truncation)

        position_ids = compute_position_id_with_mask(attention_mask)

        row_dict['input_ids'] = input_ids[0]
        row_dict['attention_mask'] = attention_mask[0]
        row_dict['position_ids'] = position_ids[0]
        
        tgt = row_dict.pop(self.target_key)
        sample = np.random.rand() < self.sample_target_ratio
        
        if tgt is not None and sample is True:
            tgt = tgt[0]
        
            if prompt_with_chat_template.endswith('<think>\n') and tgt['content'].startswith('<think>\n'):
                tgt['content'] = tgt['content'][len('<think>\n'):]
            tgt_input_ids = self.tokenizer(tgt['content'], add_special_tokens=False, return_tensors='pt')['input_ids'].reshape(-1) # [1, l]

            # NOTE: we don't need to do this because we add eos token id at mix_vllm_rollout.py
            
            # if tgt_input_ids[-1].item() != self.tokenizer.eos_token_id:
            #     eos_tensor = torch.tensor([self.tokenizer.eos_token_id], device=tgt_input_ids.device, dtype=tgt_input_ids.dtype).reshape(-1)
            #     tgt_input_ids = torch.cat([tgt_input_ids, eos_tensor], dim=-1)
            
            tgt_input_ids = tgt_input_ids.reshape(1, -1)
        else:
            tgt_input_ids = torch.tensor([], dtype=torch.long).reshape(1, 0) # empty target, will be pad to max_target_length

        # padding or truncate
        sequence_length = tgt_input_ids.shape[-1]
        if sequence_length < self.max_target_length:
            # right pad for tgt_input_ids
            tgt_input_ids = pad_sequence_to_length(tgt_input_ids,
                                            max_seq_len=self.max_target_length,
                                            pad_token_id=self.tokenizer.pad_token_id,
                                            left_pad=False)
        else:
            assert self.truncation in ('right', 'error')
            tgt_input_ids = tgt_input_ids[:, :self.max_target_length]
        
        tgt_input_ids = tgt_input_ids.squeeze(0)

        row_dict['tgt_input_ids'] = tgt_input_ids
        
        # process target_list
        if getattr(self, 'target_list_key', "target_list_key") in row_dict:
            target_list = row_dict.pop(self.target_list_key)
            if target_list is None:
                tgt_input_ids_lst = [torch.zeros_like(tgt_input_ids).fill_(self.tokenizer.pad_token_id)] * self.max_num_targets
            else:
                tgt_input_ids_lst = [self._process_target(tgt, prompt_with_chat_template, add_eos=True) for tgt in target_list]
                if len(tgt_input_ids_lst) <= self.max_num_targets:
                    tgt_input_ids_lst.extend([torch.zeros_like(tgt_input_ids_lst[0]).fill_(self.tokenizer.pad_token_id)] * (self.max_num_targets - len(tgt_input_ids_lst)))
                else:
                    tgt_input_ids_lst = tgt_input_ids_lst[:self.max_num_targets]
            row_dict['tgt_input_ids_lst'] = torch.stack(tgt_input_ids_lst, dim=0) # [max_num_targets, max_target_length]
        
        if getattr(self, 'target_probs_key', "target_probs_key") in row_dict:
            target_probs = row_dict.pop(self.target_probs_key)
            if target_probs is not None:
                target_probs_pt = torch.tensor(target_probs, dtype=torch.float32, device=tgt_input_ids.device)
                target_probs_pt = target_probs_pt.reshape(1, -1)
                # truncation
                # prompt_len = (input_ids[0] != self.tokenizer.pad_token_id).sum()
                tgt_len = (tgt_input_ids != self.tokenizer.pad_token_id).sum()
                try:
                    assert target_probs_pt.shape[-1] == tgt_len+1
                except Exception as e:
                    breakpoint()
                
                # same padding as tgt_input_ids
                if target_probs_pt.shape[-1] < self.max_target_length:
                    target_probs_pt = pad_sequence_to_length(target_probs_pt,
                                                max_seq_len=self.max_target_length,
                                                pad_token_id=-1,
                                                left_pad=False)
                else:
                    assert self.truncation in ('right', 'error')
                    target_probs_pt = target_probs_pt[:, :self.max_target_length]
                row_dict['target_probs'] = target_probs_pt.squeeze(0) # [max_target_length]
            else:
                row_dict['target_probs'] = torch.zeros_like(tgt_input_ids, dtype=torch.float32, device=tgt_input_ids.device).fill_(-1)

        # encode prompts without chat template
        if self.return_raw_chat:
            row_dict['raw_prompt'] = chat.tolist()

        # add index for each prompt
        index = row_dict.get("extra_info", {}).get("index", 0)
        row_dict["index"] = index

        return row_dict

    def _process_target(self, tgt: str, prompt: str, add_eos=False) -> torch.Tensor:
        if prompt.endswith('<think>\n') and tgt.startswith('<think>\n'):
            tgt = tgt[len('<think>\n'):]
        tgt_input_ids = self.tokenizer(tgt, add_special_tokens=False, return_tensors='pt')['input_ids'].reshape(-1) # [1, l]
        if add_eos:
            tgt_input_ids = torch.cat([tgt_input_ids, torch.tensor([self.tokenizer.eos_token_id], device=tgt_input_ids.device, dtype=tgt_input_ids.dtype).reshape(-1)])

        tgt_input_ids = tgt_input_ids.reshape(1, -1)
        # padding or truncate
        sequence_length = tgt_input_ids.shape[-1]
        if sequence_length < self.max_target_length:
            # right pad for tgt_input_ids
            tgt_input_ids = pad_sequence_to_length(tgt_input_ids,
                                            max_seq_len=self.max_target_length,
                                            pad_token_id=self.tokenizer.pad_token_id,
                                            left_pad=False)
        else:
            assert self.truncation in ('right', 'error')
            tgt_input_ids = tgt_input_ids[:, :self.max_target_length]
        
        tgt_input_ids = tgt_input_ids.squeeze(0)

        return tgt_input_ids

from verl import DataProto
class BufferedDataLoader:
    def __init__(self, dataloader):
        self.dataloader = dataloader
        self.batch_size = dataloader.batch_size
        self.buffer = []
        self.dataloader_iter = None

    def start_new_epoch(self):
        """Reset for new epoch"""
        self.dataloader_iter = iter(self.dataloader)

    def get_next_batch(self):
        try:
            return next(self.dataloader_iter)
        except StopIteration:
            raise StopIteration

    def __len__(self):
        return len(self.dataloader)

    def add_to_buffer(self, samples):
        if len(self.buffer) == 0:
            self.buffer = samples
        else:
            self.buffer = DataProto.concat([self.buffer, samples])

    def get_from_buffer(self, count, dp_size):
        if count > self.buffer_size():
            count = (self.buffer_size() // dp_size) * dp_size
        samples = self.buffer.slice(range(0, count))
        self.buffer = self.buffer.slice(range(count, self.buffer_size()))
        return samples

    def buffer_size(self):
        return len(self.buffer)

import torch

class ResumableRandomSampler(torch.utils.data.Sampler):
    r"""Samples elements randomly. If without replacement, then sample from a shuffled dataset.
    If with replacement, then user can specify :attr:`num_samples` to draw.
    Arguments:
        data_source (Dataset): dataset to sample from
        replacement (bool): samples are drawn on-demand with replacement if ``True``, default=``False``
        num_samples (int): number of samples to draw, default=`len(dataset)`. This argument
            is supposed to be specified only when `replacement` is ``True``.
        generator (Generator): Generator used in sampling.
    """
    #data_source: Sized
    #replacement: bool

    def __init__(self, data_source):
        self.data_source = data_source
        self.generator = torch.Generator()
        self.generator.manual_seed(47)
        
        self.perm_index = 0
        self.perm = torch.randperm(self.num_samples, generator=self.generator)
        
    @property
    def num_samples(self) -> int:
        return len(self.data_source)

    def __iter__(self):
        if self.perm_index >= len(self.perm):
            self.perm_index = 0
            self.perm = torch.randperm(self.num_samples, generator=self.generator)
            
        while self.perm_index < len(self.perm):
            self.perm_index += 1
            yield self.perm[self.perm_index-1].item() # the output index should be int

    def __len__(self):
        return self.num_samples
    
    def get_state(self):
        return {"perm": self.perm, "perm_index": self.perm_index, "generator_state": self.generator.get_state()}
    
    def set_state(self, state):
        self.perm = state["perm"]
        self.perm_index = state["perm_index"]
        self.generator.set_state(state["generator_state"])

def _pre_process_inputs_right_pad(pad_token_id, prompt_token_ids: torch.Tensor) -> List[int]:
    # remove the left padding in the prompt token_id
    # pad_token_id = self.llm_engine.tokenizer.pad_token_id if self.llm_engine.tokenizer.pad_token_id is not None else self.llm_engine.tokenizer.eos_token_id
    non_pad_index = torch.nonzero(prompt_token_ids != pad_token_id, as_tuple=False)
    token_ids = prompt_token_ids[:non_pad_index[-1][0]].tolist()
    return token_ids