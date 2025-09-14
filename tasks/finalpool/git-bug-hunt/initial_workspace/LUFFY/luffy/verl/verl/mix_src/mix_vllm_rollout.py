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
The vllm_rollout that can be applied in different backend
When working with FSDP:
- Use DTensor weight loader (recommended) or HF weight loader
- Utilize state_dict from the FSDP to synchronize the weights among tp ranks in vLLM
When working with Megatron:
- Use Megatron weight loader
- During training, only the current pp stage holds the parameters
- Before inference, broadcast the parameters of the current pp rank to all other pp ranks (all pp ranks holds all the parameters)
- Bind the parameters to the inference engine
- Do inference in tp. pp is treated as additional dp
- After inference, all the parameters that doesn't belong to this pp rank is freed.
"""
from typing import List
from contextlib import contextmanager
from omegaconf import DictConfig
import torch
import torch.distributed
from tensordict import TensorDict
import traceback
from torch import nn

from verl import DataProto
from verl.utils.torch_functional import get_eos_mask, pad_sequence_to_length
from verl.workers.rollout.base import BaseRollout
from verl.third_party.vllm import LLM, vllm_version
from verl.third_party.vllm import parallel_state as vllm_ps
from vllm import SamplingParams

# TODO
# 1. support pp in vllm
# 2. passing tokenizer is not necessary? no encoding/decoding is happending here
# 3. simplify init logics

import logging
import os
logger = logging.getLogger(__file__)
logger.setLevel(os.getenv('VERL_PPO_LOGGING_LEVEL', 'INFO'))

# from pprint import pprint

# NOTE(sgm): add for verl. We can optimize it by making the dataloader yield List[int] without padding.
def _pre_process_inputs(pad_token_id, prompt_token_ids: torch.Tensor) -> List[int]:
    # remove the left padding in the prompt token_id
    # pad_token_id = self.llm_engine.tokenizer.pad_token_id if self.llm_engine.tokenizer.pad_token_id is not None else self.llm_engine.tokenizer.eos_token_id
    non_pad_index = torch.nonzero(prompt_token_ids != pad_token_id, as_tuple=False)[0][0]
    token_ids = prompt_token_ids[non_pad_index:].tolist()
    return token_ids


def _pre_process_inputs_right_pad(pad_token_id, prompt_token_ids: torch.Tensor) -> List[int]:
    # remove the left padding in the prompt token_id
    # pad_token_id = self.llm_engine.tokenizer.pad_token_id if self.llm_engine.tokenizer.pad_token_id is not None else self.llm_engine.tokenizer.eos_token_id
    non_pad_index = torch.nonzero(prompt_token_ids != pad_token_id, as_tuple=False)
    if len(non_pad_index) == 0:
        return []
    else:
        token_ids = prompt_token_ids[:non_pad_index[-1][0]+1].tolist()
    return token_ids

from verl.workers.rollout.vllm_rollout import vLLMRollout

class MIXvLLMRollout(vLLMRollout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix_strategy = self.config.get('prefix_strategy', 'random')
        
        self.prefix_steps = self.config.get('prefix_steps', 300)
        self.prefix_linear_max_ratio = self.config.get('prefix_linear_max_ratio', 0.8)
        if self.prefix_strategy == 'linear':
            # self.prefix_linear_max_ratio = self.config.get('prefix_linear_max_ratio', 0.8)
            pass
        elif self.prefix_strategy == 'linear_max':
            self.prefix_ratio_windows = [(0, i*self.prefix_linear_max_ratio/10) for i in range(10, 0, -1)]
            self.prefix_step_windows = [(i*self.prefix_steps/10, (i+1)*self.prefix_steps/10) for i in range(10)]
        elif self.prefix_strategy == 'linear_variance':
            # self.prefix_linear_max_ratio = self.config.get('prefix_linear_max_ratio', 0.8)
            self.prefix_lienar_max_var = self.config.get('prefix_lienar_max_var', 0.1)
        elif self.prefix_strategy == 'reverse_linear':
            # self.prefix_linear_max_ratio = self.config.get('prefix_linear_max_ratio', 0.8)
            self.prefix_ratio_windows = [(0, (i+1)*self.prefix_linear_max_ratio/10) for i in range(10)]
            self.prefix_step_windows = [(i*self.prefix_steps/10, (i+1)*self.prefix_steps/10) for i in range(10)]
        elif self.prefix_strategy == 'fixed':
            assert self.config.prefix_share_across_samples == False, "Fixed strategy could not work with prefix_share_across_samples=True ! "
            # self.prefix_fixed_num = self.config.get('prefix_fixed_num', 2)
            n_prefix = self.config.n_prefix if self.config.n_prefix != -1 else self.config.n
            ratio_step = (self.config.max_prefix_ratio - self.config.min_prefix_ratio) / (n_prefix-1)
            self.prefix_fix_ratios = [self.config.min_prefix_ratio + i*ratio_step for i in range(n_prefix)]

    @torch.no_grad()
    def generate_sequences(self, prompts: DataProto, max_retries: int = 1e9, **kwargs) -> DataProto:
        """Generate sequences using vLLM engine with retry logic for failures.

        Args:
            prompts (DataProto): Input prompts containing batch data with input_ids, attention_mask,
                position_ids and meta_info.
            max_retries (int, optional): Maximum number of retries on failure. Defaults to 1e9.
            **kwargs: Additional sampling parameters to override defaults.

        Returns:
            DataProto: Generated sequences containing:
                - prompts: Original input token ids
                - responses: Generated response token ids
                - input_ids: Concatenated prompt and response tokens
                - attention_mask: Attention mask for full sequence
                - position_ids: Position ids for full sequence

        Raises:
            RuntimeError: If generation fails after max_retries attempts.
        """
        max_retries = int(max_retries)
        for attempt in range(max_retries):
            try:
                # Rebuild vLLM cache engine if configured
                if self.config.free_cache_engine:
                    self.inference_engine.init_cache_engine()
                    
                # Extract input tensors from prompt batch
                idx = prompts.batch['input_ids']
                attention_mask = prompts.batch['attention_mask']
                position_ids = prompts.batch['position_ids']
                eos_token_id = prompts.meta_info['eos_token_id']

                # we use repeat to get n generations for each prompt
                # Pre-process input token ids
                batch_size = idx.size(0)
                idx_list = [
                    _pre_process_inputs(self.pad_token_id, idx[i])
                    for i in range(batch_size)
                ]
                # repeat idx_list to get n generations for each prompt
                do_sample = prompts.meta_info.get('do_sample', True)
                if do_sample:
                    idx_list = sum([[idx_list[i]] * self.config.n for i in range(len(idx_list))], [])
                
                prefix_ratios = None
                # logger.info('after idx_list length', len(idx_list))
                tgt_input_ids = None
                if 'tgt_input_ids' in prompts.batch: # in train mode
                    tgt_input_ids = prompts.batch['tgt_input_ids']  # [bsz, tgt_len]

                    # add eos token id to the end of the target
                    tgt_list = [
                        _pre_process_inputs_right_pad(self.pad_token_id, tgt_input_ids[i]) for i in range(batch_size)
                    ]
                    # NOTE: be careful with the case when tgt_input_ids is empty.
                    # where it only contains paddings
                    # in this case, we should not add eos token id to the end of the target
                    tgt_list = [
                        tgt_list[i] + [self.tokenizer.eos_token_id,] if len(tgt_list[i]) > 0 else tgt_list[i]
                        for i in range(batch_size)
                    ]
                    
                    tgt_list = sum([[tgt_list[i]] * self.config.n for i in range(len(tgt_list))], [])
                    
                    global_steps = prompts.meta_info['global_steps'] - 1 # we start from 1
                    import random
                    if not self.config.prefix_share_across_samples:
                        assert self.config.prefix_strategy != 'linear', "Linear strategy is not implemented with prefix_share_across_samples=True ! "
                        if self.config.n_prefix == -1:
                            if self.config.prefix_strategy == 'random':
                                prefix_ratios = [random.uniform(self.config.min_prefix_ratio, self.config.max_prefix_ratio) for _ in range(len(tgt_list))]
                            elif self.config.prefix_strategy == 'reverse_linear' or self.config.prefix_strategy == 'linear_max':
                                w_idx = -1
                                for i in range(len(self.prefix_step_windows)):
                                    if global_steps >= self.prefix_step_windows[i][0] and global_steps <= self.prefix_step_windows[i][1]:
                                        w_idx = i
                                        break
                                prefix_ratios = [random.uniform(self.prefix_ratio_windows[w_idx][0], self.prefix_ratio_windows[w_idx][1]) for _ in range(len(tgt_list))]
                            elif self.config.prefix_strategy == 'fixed':
                                prefix_ratios = sum([self.prefix_fix_ratios for i in range(batch_size)], [])
                        else:
                            assert self.config.n_prefix <= self.config.n, f"n_prefix {self.config.n_prefix} must be less than or equal to n {self.config.n}"
                            assert len(tgt_list) == self.config.n * batch_size
                            prefix_ratios = []
                            for i in range(batch_size):
                                if self.config.prefix_strategy == 'random':
                                    prefix_ratios.extend([random.uniform(self.config.min_prefix_ratio, self.config.max_prefix_ratio) for _ in range(self.config.n_prefix)])
                                elif self.config.prefix_strategy == 'reverse_linear' or self.config.prefix_strategy == 'linear_max':
                                    w_idx = -1
                                    for i in range(len(self.prefix_step_windows)):
                                        if global_steps >= self.prefix_step_windows[i][0] and global_steps <= self.prefix_step_windows[i][1]:
                                            w_idx = i
                                            break
                                    prefix_ratios.extend([random.uniform(self.prefix_ratio_windows[w_idx][0], self.prefix_ratio_windows[w_idx][1]) for _ in range(self.config.n_prefix)])
                                elif self.config.prefix_strategy == 'fixed':
                                    prefix_ratios.extend(self.prefix_fix_ratios[:])
                                else: raise NotImplementedError(f"Prefix strategy {self.config.prefix_strategy} is not implemented! ")
                                
                                prefix_ratios.extend([0.0] * (self.config.n - self.config.n_prefix))
                            assert len(prefix_ratios) == len(tgt_list)
                    else:
                        if self.config.prefix_strategy == 'linear':
                            ratio = min((global_steps / self.prefix_steps), 1.0)
                            prefix_ratio_base = self.prefix_linear_max_ratio * (1-ratio)
                        else: # default, use random prefix ratio
                            prefix_ratio_base = None
                            
                        assert self.config.n_prefix <= self.config.n, f"n_prefix {self.config.n_prefix} must be less than or equal to n {self.config.n}"
                        assert len(tgt_list) == self.config.n * batch_size
                        prefix_ratios = []
                        for i in range(batch_size):
                            prefix_ratio = prefix_ratio_base if prefix_ratio_base is not None else random.uniform(self.config.min_prefix_ratio, self.config.max_prefix_ratio)

                            if self.config.n_prefix > 0:
                                prefix_ratios.extend([prefix_ratio] * self.config.n_prefix)
                                prefix_ratios.extend([0.0] * (self.config.n - self.config.n_prefix))
                            else:
                                logger.info(f"Prefix share across samples enabled! n_prefix is 0, n is set to {self.config.n}")
                                prefix_ratios.extend([prefix_ratio] * self.config.n)
                        assert len(prefix_ratios) == len(tgt_list)
                    
                    prefix_list = [tgt_list[i][:int(len(tgt_list[i]) * prefix_ratios[i])] for i in range(len(tgt_list))]
                    idx_list = [idx_list[i] + prefix_list[i] for i in range(len(idx_list))]
                else: # in eval mode, we don't have tgt_input_ids
                    tgt_list = None
                
                # self.update_sampling_params(n=1)
                
                # Configure sampling parameters
                if not do_sample:
                    kwargs = {
                        'best_of': 1,
                        'top_p': 1.0,
                        'top_k': -1,
                        'min_p': 0.0,
                        'temperature': 0,
                        'n': 1
                    }
                if prompts.meta_info.get('val_temperature', None):
                    kwargs['temperature'] = prompts.meta_info['val_temperature']

                # we use n=1 because we have repeated the idx_list to get n generations for each prompt
                kwargs['n'] = 1
                # should only affect train mode.
                # if 'tgt_input_ids' in prompts.batch and self.config.min_prefix_ratio == 1.0: 
                    # kwargs['max_tokens'] = 1
                # Generate sequences
                with self.update_sampling_params(**kwargs):
                    output = self.inference_engine.generate(
                        prompts=None,
                        sampling_params=self.sampling_params,
                        prompt_token_ids=idx_list,
                        use_tqdm=False)

                # Process outputs
                response = output[0].to(idx.device)
                # logger.info('example response', response)
                # logger.info('example response shape', response.shape)
                
                if 'tgt_input_ids' in prompts.batch:
                    # put the prefix back to the response
                    try:
                        resp_list = [
                            _pre_process_inputs_right_pad(self.pad_token_id, resp)
                            for resp in response
                        ]
                    except:
                        breakpoint()
                    
                    # get prefix_mask and concat_resp_list
                    concat_resp_list = []
                    prefix_mask = torch.zeros([len(resp_list), self.config.response_length], dtype=torch.bool).to(idx.device)
                    for i in range(len(resp_list)):
                        concat_resp_list.append(torch.tensor(prefix_list[i] + resp_list[i]))
                        prefix_len = min(len(prefix_list[i]), self.config.response_length)
                        prefix_mask[i, :prefix_len] = True

                    resp_max_len = max([len(resp) for resp in concat_resp_list])
                    # prepare batch response, right pad to the max length
                    tt = torch.ones(len(concat_resp_list), resp_max_len).fill_(self.pad_token_id)
                    for i in range(len(concat_resp_list)):
                        tt[i][:len(concat_resp_list[i])] = concat_resp_list[i].clone().detach()
                    response = tt.to(idx.device)[:, :self.config.response_length].to(response.dtype)
                else:
                    prefix_mask = torch.tensor([]) # empty dummy tensor
                
                # Pad sequences if needed
                if response.shape[1] < self.config.response_length:
                    response = pad_sequence_to_length(
                        response, self.config.response_length, self.pad_token_id)

                # Handle multiple samples per prompt
                if self.config.n > 1 and do_sample:
                    idx = idx.repeat_interleave(self.config.n, dim=0)
                    if tgt_input_ids is not None:
                        tgt_input_ids = tgt_input_ids.repeat_interleave(
                            self.config.n, dim=0)
                    else:
                        tgt_input_ids = None
                    attention_mask = attention_mask.repeat_interleave(
                        self.config.n, dim=0)
                    position_ids = position_ids.repeat_interleave(
                        self.config.n, dim=0)
                    batch_size = batch_size * self.config.n

                # Concatenate prompt and response
                seq = torch.cat([idx, response], dim=-1)

                # Create position IDs and attention mask for full sequence
                response_length = response.size(1)
                delta_position_id = torch.arange(
                    1, response_length + 1, device=position_ids.device)
                delta_position_id = delta_position_id.unsqueeze(0).repeat(
                    batch_size, 1)

                response_position_ids = position_ids[:, -1:] + delta_position_id
                position_ids = torch.cat([position_ids, response_position_ids],
                                       dim=-1)
                response_attention_mask = get_eos_mask(
                    response_id=response,
                    eos_token=eos_token_id,
                    dtype=attention_mask.dtype)
                attention_mask = torch.cat(
                    (attention_mask, response_attention_mask), dim=-1)

                # Construct output batch
                batch = TensorDict(
                    {
                        'prompts': idx,
                        'responses': response,
                        'input_ids': seq,
                        'attention_mask': attention_mask,
                        'position_ids': position_ids,
                    },
                    batch_size=batch_size)
                
                if tgt_input_ids is not None:
                    batch['tgt_input_ids'] = tgt_input_ids
                
                if prefix_mask.shape[0] > 0:
                    batch['prefix_mask'] = prefix_mask

                # Free cache if configured
                if self.config.free_cache_engine:
                    self.inference_engine.free_cache_engine()

                if prefix_ratios is not None:
                    meta_info = {
                        'prefix_ratios': prefix_ratios,
                    }
                    return DataProto(batch=batch, meta_info=meta_info)
                else:
                    return DataProto(batch=batch)

            except Exception as e:
                traceback.print_exc()
                print("Restarting vLLM due to error: ", e)
                print("Retrying...")

                # Clean up and restart engine
                torch.cuda.empty_cache()
                if hasattr(self.inference_engine, 'free_cache_engine'):
                    self.inference_engine.free_cache_engine()
                del self.inference_engine

                # Reinitialize engine with same parameters
                self.inference_engine = LLM(
                    self.actor_module,
                    tokenizer=self.tokenizer,
                    model_hf_config=self.model_hf_config,
                    tensor_parallel_size=self.tensor_parallel_size,
                    dtype=self.config.dtype,
                    enforce_eager=self.config.enforce_eager,
                    gpu_memory_utilization=self.config.gpu_memory_utilization,
                    skip_tokenizer_init=False,
                    max_model_len=self.config.prompt_length +
                    self.config.response_length,
                    load_format=self.config.load_format)
                print("vLLM is ready to roll!")

                if attempt < max_retries - 1:
                    continue

        raise RuntimeError(
            f"Failed to generate sequences after {max_retries} attempts")

def unit_test():
    batch = DataProto.from_single_dict({
        'input_ids': torch.tensor([[1, 2, 3, 4, 5]]),
        'tgt_input_ids': torch.tensor([[1, 2, 3, 4, 5]])
    })
    idx = batch.batch['input_ids']
    tgt_input_ids = batch.batch['tgt_input_ids']
    
    batch_size = tgt_input_ids.size(0)
    
    # idx_list = [1, 2, 3, 4, 5]
    idx_list = [
        _pre_process_inputs(1, idx[i])
        for i in range(batch_size)
    ]

    idx_list = sum([[idx_list[i]] * 2 for i in range(len(idx_list))], [])

    tgt_input_ids = batch.batch['tgt_input_ids']  # [bsz, tgt_len]

    tgt_list = [
        _pre_process_inputs(1, tgt_input_ids[i])
        for i in range(batch_size)
    ]
    
    tgt_list = sum([[tgt_list[i]] * 2 for i in range(len(tgt_list))], [])
    
    import random
    prefix_ratios = [random.randint(0, 100)/100 for _ in range(len(tgt_list))]
    prefix_list = [tgt_list[i][:int(len(tgt_list[i]) * prefix_ratios[i])] for i in range(len(tgt_list))]
    idx_list = [idx_list[i] + prefix_list[i] for i in range(len(idx_list))]
    print(idx_list)
    print(tgt_list)
    print(prefix_list)

if __name__ == "__main__":
    unit_test()