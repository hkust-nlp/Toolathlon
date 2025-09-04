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
FSDP PPO Trainer with Ray-based single controller.
This trainer supports model-agonistic model initialization with huggingface
"""

import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pprint import pprint
from typing import Type, Dict
from collections import defaultdict, Counter

import numpy as np
from codetiming import Timer
from omegaconf import OmegaConf, open_dict
from verl import DataProto
from verl.protocol import pad_dataproto_to_divisor, unpad_dataproto, DataProtoItem
from verl.single_controller.base import Worker
from verl.single_controller.ray import RayResourcePool, RayWorkerGroup, RayClassWithInitArgs
from verl.single_controller.ray.base import create_colocated_worker_cls
from verl.trainer.ppo import core_algos
from verl.utils.seqlen_balancing import get_seqlen_balanced_partitions, log_seqlen_unbalance

import torch

from verl.trainer.ppo.ray_trainer import (
    RayPPOTrainer, 
    Role, 
    ResourcePoolManager, 
    WorkerType, 
    _timer, 
    # compute_data_metrics, 
    compute_timing_metrics, 
    dataprotoitem_to_dataproto, 
    # compute_advantage, 
    reduce_metrics
)
from verl.utils.torch_functional import masked_mean
from .mix_trainer import MIXRayPPOTrainer, compute_advantage, apply_kl_penalty, compute_data_metrics_ours


class MIXRayPPOTrainerAccRebatch(MIXRayPPOTrainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer_batch = []

    def _create_dataloader(self):
        # TODO: we have to make sure the batch size is divisible by the dp size
        from torch.utils.data import DataLoader, RandomSampler, SequentialSampler
        from verl.utils.dataset.rl_dataset import RLHFDataset, collate_fn
        from .rl_dataset_with_target import RLHFDatasetWithTarget
        self.train_dataset = RLHFDatasetWithTarget(parquet_files=self.config.data.train_files,
                                         tokenizer=self.tokenizer,
                                         prompt_key=self.config.data.prompt_key,
                                         max_prompt_length=self.config.data.max_prompt_length,
                                         filter_prompts=True,
                                         return_raw_chat=self.config.data.get('return_raw_chat', False),
                                         truncation='error',
                                         max_target_length=self.config.actor_rollout_ref.rollout.max_prefix_len,
                                         filter_targets=self.config.data.get('filter_targets', False),
                                         sample_target_ratio=self.config.data.get('sample_target_ratio', 1.0))

        # use sampler for better ckpt resume
        if self.config.data.shuffle:
            train_dataloader_generator = torch.Generator()
            train_dataloader_generator.manual_seed(self.config.data.get('seed', 1))
            sampler = RandomSampler(data_source=self.train_dataset, generator=train_dataloader_generator)
        else:
            sampler = SequentialSampler(data_source=self.train_dataset)

        from .rl_dataset_with_target import BufferedDataLoader
        self.train_dataloader = BufferedDataLoader(DataLoader(dataset=self.train_dataset,
                                           batch_size=self.config.data.train_batch_size,
                                           drop_last=True,
                                           collate_fn=collate_fn,
                                           sampler=sampler))
        
        self.val_dataset = RLHFDataset(parquet_files=self.config.data.val_files,
                                       tokenizer=self.tokenizer,
                                       prompt_key=self.config.data.prompt_key,
                                       max_prompt_length=self.config.data.max_prompt_length,
                                       filter_prompts=True,
                                       return_raw_chat=self.config.data.get('return_raw_chat', False),
                                       truncation='error')
        self.val_dataloader = DataLoader(dataset=self.val_dataset,
                                         batch_size=len(self.val_dataset),
                                         shuffle=True,
                                         drop_last=True,
                                         collate_fn=collate_fn)

        assert len(self.train_dataloader) >= 1
        assert len(self.val_dataloader) >= 1

        print(f'Size of train dataloader: {len(self.train_dataloader)}')
        print(f'Size of val dataloader: {len(self.val_dataloader)}')

        # inject total_training_steps to actor/critic optim_config. This is hacky.
        total_training_steps = len(self.train_dataloader) * self.config.trainer.total_epochs

        if self.config.trainer.total_training_steps is not None:
            total_training_steps = self.config.trainer.total_training_steps

        self.total_training_steps = total_training_steps
        print(f'Total training steps: {self.total_training_steps}')

        OmegaConf.set_struct(self.config, True)
        with open_dict(self.config):
            self.config.actor_rollout_ref.actor.optim.total_training_steps = total_training_steps
            self.config.critic.optim.total_training_steps = total_training_steps

    def fit(self):
        """
        The training loop of PPO.
        The driver process only need to call the compute functions of the worker group through RPC to construct the PPO dataflow.
        The light-weight advantage computation is done on the driver process.
        """
        from verl.utils.tracking import Tracking
        from omegaconf import OmegaConf

        logger = Tracking(project_name=self.config.trainer.project_name,
                          experiment_name=self.config.trainer.experiment_name,
                          default_backend=self.config.trainer.logger,
                          config=OmegaConf.to_container(self.config, resolve=True))

        self.global_steps = 0

        # load checkpoint before doing anything
        self._load_checkpoint()

        # perform validation before training
        if self.val_reward_fn is not None and self.config.trainer.get('val_before_train', True):
            val_metrics = self._validate()
            pprint(f'Initial validation metrics: {val_metrics}')
            logger.log(data=val_metrics, step=self.global_steps)
            if self.config.trainer.get('val_only', False):
                return

        # we start from step 1
        self.global_steps += 1


        for _ in range(self.config.trainer.total_epochs):

            self.train_dataloader.start_new_epoch() # NOTE: does this affect continue runnning?

            while True:  # batch iter
                metrics = {}
                timing_raw = {}

                with _timer('step', timing_raw):
                    valid_batch = []
                    buffer_batch = []
                    
                    if self.train_dataloader.buffer_size() > 0:
                        buffer_batch = self.train_dataloader.get_from_buffer(batch_size, self.actor_rollout_wg.world_size)

                    batch_size = self.config.data.train_batch_size
                    n_samples = self.config.actor_rollout_ref.rollout.n
                
                    while len(valid_batch) < batch_size * n_samples:  # construct a valid batch
                        try:
                            batch_dict = self.train_dataloader.get_next_batch()
                        except StopIteration:
                            break
                        
                        batch: DataProto = DataProto.from_single_dict(batch_dict)

                        if len(buffer_batch) > 0:
                            try:
                                if 'prefix_ratios' in buffer_batch.meta_info.keys():
                                    buffer_batch.meta_info.pop('prefix_ratios')
                                if 'prefix_ratios' in batch.meta_info.keys():
                                    batch.meta_info.pop('prefix_ratios')
                                batch = DataProto.concat([buffer_batch, batch])
                                buffer_batch = []
                            except Exception as e:
                                breakpoint()

                        gen_batch = batch.pop(batch_keys=['input_ids', 'attention_mask', 'position_ids', 'tgt_input_ids'])
                        gen_batch.meta_info['global_steps'] = self.global_steps
                        
                        # generate a batch
                        with _timer('gen', timing_raw):
                            gen_batch_output = self.actor_rollout_wg.generate_sequences(gen_batch)
        
                        batch.non_tensor_batch['uid'] = np.array([str(uuid.uuid4()) for _ in range(len(batch.batch))],
                                                                 dtype=object)
                        batch = batch.repeat(repeat_times=self.config.actor_rollout_ref.rollout.n, interleave=True)
                        try:
                            batch = batch.union(gen_batch_output)
                        except Exception as e:
                            breakpoint()

                        # log avg prefix ratio
                        if 'prefix_ratios' in gen_batch_output.meta_info.keys():
                            metrics['batch/avg_prefix_ratio'] = float(np.mean(gen_batch_output.meta_info['prefix_ratios']))

                        # compute values
                        if self.use_critic:
                            with _timer('values', timing_raw):
                                values = self.critic_wg.compute_values(batch)
                                batch = batch.union(values)

                        with _timer('adv', timing_raw):
                            # compute scores using reward model and/or reward function
                            if self.use_rm:
                                reward_tensor = self.rm_wg.compute_rm_score(batch)
                                batch = batch.union(reward_tensor)

                            reward_tensor = self.reward_fn(batch) # [bsz, l], only the last valid token has reward
                            batch.batch['token_level_scores'] = reward_tensor
                        
                        # Group rewards by uid
                        uids = batch.non_tensor_batch['uid']
                        unique_uids = np.unique(uids)
                        valid_mask = torch.ones(len(uids), dtype=torch.bool)
                        
                        if self.config.data.reward_impl_version == 0:
                            fail_value = 0
                            success_value = 1
                            format_value = -1 # not defined.
                        elif self.config.data.reward_impl_version == 1:
                            fail_value = -0.5
                            success_value = 1
                            format_value = -1
                        elif self.config.data.reward_impl_version == 2:
                            fail_value = 0
                            success_value = 1
                            format_value = -1
                        elif self.config.data.reward_impl_version == 3:
                            fail_value = 0
                            success_value = 1
                            format_value = -1
                        elif self.config.data.reward_impl_version == 4:
                            fail_value = 0
                            success_value = 1
                            format_value = -1
                        else:
                            raise ValueError(f'Invalid reward implementation version: {self.config.data.reward_impl_version}')
                        
                        solve_none = 0
                        solve_all = 0
                        solve_none_format = 0
                        for uid in unique_uids:
                            uid_mask = uids == uid
                            uid_rewards = reward_tensor[uid_mask].sum(-1)  # Sum rewards for each sequence
                            
                            # Check if all rewards are 0 or all are 1 for this uid
                            if (uid_rewards == fail_value).all():
                                valid_mask[uid_mask] = False
                                solve_none += 1
                            elif (uid_rewards == success_value).all():
                                valid_mask[uid_mask] = False
                                solve_all += 1
                            elif (uid_rewards == format_value).all():
                                valid_mask[uid_mask] = False
                                solve_none_format += 1

                        if self.config.trainer.skip_valid_mask:
                            valid_mask[:] = True
                        # Log to metrics
                        metrics['batch/solve_none'] = solve_none
                        metrics['batch/solve_none_format'] = solve_none_format
                        metrics['batch/solve_all'] = solve_all

                        # add more metrics
                        metrics['batch/solved'] = (reward_tensor.sum(-1) == success_value).sum().item() / len(uids)
                        metrics['batch/failed'] = (reward_tensor.sum(-1) == fail_value).sum().item() / len(uids)
                        # add on-policy metrics
                        prefix_mask = batch.batch['prefix_mask']
                        off_policy_mask = prefix_mask.any(-1)
                        on_policy_mask = ~off_policy_mask
                        metrics['batch/on_solved'] = (reward_tensor[on_policy_mask].sum(-1) == success_value).sum().item() / (on_policy_mask.sum().item() + 1e-6)
                        metrics['batch/off_solved'] = (reward_tensor[off_policy_mask].sum(-1) == success_value).sum().item() / (off_policy_mask.sum().item() + 1e-6)

                        if self.config.data.get('filter_accuracy', False):
                            batch = self.filter(batch.batch['token_level_scores'], batch, self.config.actor_rollout_ref.rollout.n)
                        
                        # if len(buffer_batch) > 0:
                        #     batch = DataProto.concat([buffer_batch, batch])
                        #     buffer_batch = []

                        if len(valid_batch) == 0:
                            valid_batch = batch
                        else:
                            valid_batch = DataProto.concat([valid_batch, batch])
                    
                        print(
                            f"collected {len(valid_batch)} / {batch_size * n_samples} rollouts and each prompt has {n_samples} responses")
                    
                    if len(valid_batch) < batch_size * n_samples: 
                        break
                    elif len(valid_batch) > batch_size * n_samples:
                        valid_batch = self.add_to_buffer(valid_batch, batch_size, n_samples)
                        
                    batch = valid_batch
                    reward_tensor = batch.batch['token_level_scores']
                    
                    # recompute old_log_probs
                    with _timer('old_log_prob', timing_raw):
                        old_log_prob = self.actor_rollout_wg.compute_log_prob(batch)
                        batch = batch.union(old_log_prob)

                    if self.use_reference_policy:
                        # compute reference log_prob
                        with _timer('ref', timing_raw):
                            ref_log_prob = self.ref_policy_wg.compute_ref_log_prob(batch)
                            batch = batch.union(ref_log_prob)

                    # compute rewards with KL penalty if needed

                    # Note: This kl penalty applied directly over the rewards is disabled for GRPO. The kl penalty is applied at dp_actor.py
                    # where it is subtracted directly from the policy loss

                    # compute rewards. apply_kl_penalty if available
                    if not self.config.actor_rollout_ref.actor.get('use_kl_loss', False):
                        batch, kl_metrics = apply_kl_penalty(batch,
                                                                kl_ctrl=self.kl_ctrl,
                                                                kl_penalty=self.config.algorithm.kl_penalty)
                        metrics.update(kl_metrics)
                    else:
                        batch.batch['token_level_rewards'] = batch.batch['token_level_scores']


                    # NOTE: the advantages are the same for all tokens in the response
                    # compute advantages, executed on the driver process
                    batch = compute_advantage(batch,
                                                adv_estimator=self.config.algorithm.adv_estimator,
                                                gamma=self.config.algorithm.gamma,
                                                lam=self.config.algorithm.lam,
                                                num_repeat=self.config.actor_rollout_ref.rollout.n,
                                                grpo_use_std=self.config.algorithm.grpo_use_std)
                        
                    # compute alpha and beta for prefix reward weighting
                    prefix_mask = batch.batch['prefix_mask']
                    advantages = batch.batch['advantages']
                    assert prefix_mask.shape == advantages.shape
                    
                    alpha_weight = prefix_mask.float() * self.config.actor_rollout_ref.rollout.prefix_reward_weight_alpha
                    beta_weight = (~prefix_mask).float() * self.config.actor_rollout_ref.rollout.prefix_reward_weight_beta
                    prefix_weight = alpha_weight + beta_weight
                    batch.batch['advantages'] = prefix_weight * advantages

                    # compute on-policy probs baseline for off-policy data
                    if self.config.actor_rollout_ref.actor.get('use_off_policy_loss', False) and self.config.actor_rollout_ref.actor.get('off_policy_loss_impl', 'seq') == 'seq':
                        # if self.config.
                        # print('Warning! check if your data contain on policy data, if so, make sure the off_policy_normalize=False!')
                        if self.config.actor_rollout_ref.actor.get('off_policy_normalize', True):
                            n = self.config.actor_rollout_ref.rollout.n
                            n_prefix = self.config.actor_rollout_ref.rollout.n_prefix
                            assert n_prefix != -1 and (n-n_prefix) != 1 # n-n_prefix == 1 which cause nan for std.
                            
                            l = prefix_mask.shape[-1]
                            assert prefix_mask.shape[0] % n == 0
                            bsz = prefix_mask.shape[0] // n
                            off_policy_mask = prefix_mask.any(-1) # [bsz * n]
                            on_policy_mask = ~off_policy_mask # [bsz * n]
                            logprobs = batch.batch['old_log_probs'] # [bsz * n, l]
                            op_logprobs = logprobs[on_policy_mask].reshape(bsz, -1, l) # check whether the shape is correct
                            op_tok_logprobs = masked_mean(op_logprobs, op_logprobs!=0, axis=-1) # [bsz, n_on]
                            # op_seq_logprobs = op_logprobs.mean(dim=-1) # [bsz, n_on]
                            op_logprobs_mean = op_tok_logprobs.mean(dim=-1) # [bsz]
                            op_logprobs_std = op_tok_logprobs.std(dim=-1) # [bsz]
                            
                            batch.batch['on_logprobs_mean'] = op_logprobs_mean[:, None].repeat(1, n).reshape(-1) # [bsz]
                            batch.batch['on_logprobs_std'] = op_logprobs_std[:, None].repeat(1, n).reshape(-1) # [bsz]
                        else:
                            # dummy values for code compatibility
                            bsz = batch.batch['input_ids'].shape[0]
                            dtype, device = batch.batch['advantages'].dtype, batch.batch['advantages'].device
                            batch.batch['on_logprobs_mean'] = torch.zeros(bsz).to(dtype).to(device)
                            batch.batch['on_logprobs_std'] = torch.zeros(bsz).to(dtype).to(device)
                    
                    if self.config.actor_rollout_ref.actor.get('use_sft_prefix_reward', False):
                        assert self.config.actor_rollout_ref.rollout.n_prefix == -1
                        reward_weight = self.config.actor_rollout_ref.actor.get('sft_prefix_reward_weight', 1.0)
                        batch.batch['advantages'][prefix_mask] = reward_weight / self.config.actor_rollout_ref.rollout.n
                
                    if self.config.trainer.debug is True:
                        breakpoint()
                    
                    # balance the number of valid tokens on each dp rank.
                    # Note that this breaks the order of data inside the batch.
                    # Please take care when you implement group based adv computation such as GRPO and rloo
                    self._balance_batch(batch, metrics=metrics)

                    # compute global_valid tokens
                    batch.meta_info['global_token_num'] = torch.sum(batch.batch['attention_mask'], dim=-1).tolist()

                    # update critic
                    if self.use_critic:
                        with _timer('update_critic', timing_raw):
                            critic_output = self.critic_wg.update_critic(batch)
                        critic_output_metrics = reduce_metrics(critic_output.meta_info['metrics'])
                        metrics.update(critic_output_metrics)

                    # implement critic warmup
                    if self.config.trainer.critic_warmup <= self.global_steps:
                        # update actor
                        with _timer('update_actor', timing_raw):
                            actor_output = self.actor_rollout_wg.update_actor(batch)
                        actor_output_metrics = reduce_metrics(actor_output.meta_info['metrics'])
                        metrics.update(actor_output_metrics)

                    # VALID freq seems to be wrong?
                    # validate
                    if self.val_reward_fn is not None and self.config.trainer.test_freq > 0 and \
                        self.global_steps % self.config.trainer.test_freq == 0:
                        with _timer('testing', timing_raw):
                            val_metrics: dict = self._validate()
                        metrics.update(val_metrics)

                    if self.config.trainer.save_freq > 0 and \
                            self.global_steps % self.config.trainer.save_freq == 0:
                        with _timer('save_checkpoint', timing_raw):
                            self._save_checkpoint()

                    # collect metrics
                    metrics.update(compute_data_metrics_ours(batch=batch, use_critic=self.use_critic))
                    metrics.update(compute_timing_metrics(batch=batch, timing_raw=timing_raw))

                    # TODO: make a canonical logger that supports various backend
                    logger.log(data=metrics, step=self.global_steps)

                    self.global_steps += 1

                    if self.global_steps >= self.total_training_steps:
                        # perform validation after training
                        if self.val_reward_fn is not None:
                            val_metrics = self._validate()
                            pprint(f'Final validation metrics: {val_metrics}')
                            logger.log(data=val_metrics, step=self.global_steps)
                        return

    def add_to_buffer(self, batch, batch_size, n_samples):
        buffer_length = len(batch) // n_samples - batch_size
        buffer_batch = batch.slice(range(batch_size * n_samples, (buffer_length + batch_size) * n_samples, n_samples))
        # buffer_batch.pop(non_tensor_batch_keys=['uid'], meta_info_keys=['prefix_ratios', 'global_token_num'])
        # notice that we only add prompts to buffer, and slicing strategy should be exactly consistent to what is in ray_trainer.py
        buffer_batch = buffer_batch.select(batch_keys=['input_ids', 'attention_mask', 'position_ids', 'tgt_input_ids'])
        buffer_tgt_batch = buffer_batch.pop(batch_keys=['tgt_input_ids']) #
        # slice input_ids, attention_mask and position_ids to max_prompt_length
        buffer_batch.slice_batch(start=0, length=self.config.data.max_prompt_length, dim=1)
        # put tgt_input_ids back
        buffer_batch.batch['tgt_input_ids'] = buffer_tgt_batch.batch['tgt_input_ids']
        buffer_mask = torch.ones(buffer_length + batch_size, dtype=torch.bool)
        buffer_mask[batch_size:] = False
        buffer_mask = buffer_mask.repeat_interleave(n_samples)
        batch = batch.slice(buffer_mask)
        
        buffer_batch.non_tensor_batch.pop('uid')
        buffer_batch.meta_info.pop('prefix_ratios')

        self.train_dataloader.add_to_buffer(buffer_batch)
        return batch

    def filter(self, reward_tensor, batch, n_samples):
        """
        Filter responses based on accuracy and truncation criteria.
        
        Args:
            reward_tensor: Tensor containing accuracy scores
            batch: DataProto batch containing responses
            n_samples: Number of responses per prompt
        
        Returns:
            DataProto: Filtered batch
        """
        # First do accuracy filtering if enabled
        if self.config.data.filter_accuracy:
            reward_matrix = reward_tensor.sum(-1).reshape(-1, n_samples)
            acc_tensor = torch.mean(reward_matrix, dim=-1)
            counts = Counter(acc_tensor.tolist())
            print("Accuracy distribution:", " ".join(f"{k:.2f}:{v}" for k, v in sorted(counts.items())))

            acc_mask = (acc_tensor >= self.config.data.accuracy_lower_bound) & (
                        acc_tensor <= self.config.data.accuracy_upper_bound)
        else:
            # If accuracy filtering disabled, keep all samples
            acc_mask = torch.ones(len(batch) // n_samples, dtype=torch.bool, device=reward_tensor.device)
        
        # # Then do truncation filtering if enabled
        # if self.config.data.filter_truncated:
        #     responses = batch.batch['responses']
        #     attention_mask = batch.batch['attention_mask']
        #     response_mask = attention_mask[:, -responses.size(1):]

        #     # Calculate response lengths
        #     response_lengths = response_mask.sum(-1)  # (batch_size,)
        #     response_lengths = response_lengths.reshape(-1, n_samples)  # (num_prompts, n_samples)

        #     # Get max possible length from config
        #     max_len = self.config.data.max_response_length

        #     # Check if any response in the group hits max length (indicating possible truncation)
        #     has_truncated = (response_lengths >= max_len).any(dim=-1)

        #     # Print distribution of truncated vs non-truncated
        #     truncated_counts = Counter(has_truncated.tolist())
        #     print("Truncation distribution:", 
        #         f"Truncated: {truncated_counts[True] if True in truncated_counts else 0}, "
        #         f"Non-truncated: {truncated_counts[False] if False in truncated_counts else 0}")
        #     # Keep only prompts where no response was truncated
        #     trunc_mask = ~has_truncated
        # else:
        #     # If truncation filtering disabled, keep all samples
        #     trunc_mask = torch.ones(len(batch) // n_samples, dtype=torch.bool, device=reward_tensor.device)

        # Combine both masks
        combined_mask = acc_mask # & trunc_mask

        # Expand mask to cover all samples for each prompt
        final_mask = combined_mask.repeat_interleave(n_samples)

        # Apply the mask to the batch
        filtered_batch = batch.slice(final_mask)

        print(f"Filtered batch size: {len(filtered_batch)} (from original size: {len(batch)})")
        return filtered_batch

    def _save_checkpoint(self):
        # path: given_path + `/global_step_{global_steps}` + `/actor`
        local_global_step_folder = os.path.join(self.config.trainer.default_local_dir,
                                                f'global_step_{self.global_steps}')
        actor_local_path = os.path.join(local_global_step_folder, 'actor')

        actor_remote_path = None if self.config.trainer.default_hdfs_dir is None else os.path.join(
            self.config.trainer.default_hdfs_dir, f'global_step_{self.global_steps}', 'actor')
        self.actor_rollout_wg.save_checkpoint(actor_local_path, actor_remote_path, self.global_steps)

        if self.use_critic:
            critic_local_path = os.path.join(local_global_step_folder, 'critic')
            critic_remote_path = None if self.config.trainer.default_hdfs_dir is None else os.path.join(
                self.config.trainer.default_hdfs_dir, f'global_step_{self.global_steps}', 'critic')
            self.critic_wg.save_checkpoint(critic_local_path, critic_remote_path, self.global_steps)

        # save dataloader
        dataloader_local_path = os.path.join(local_global_step_folder, 'data.pt')
        import dill
        
        # torch.save(self.train_dataloader, dataloader_local_path, pickle_module=dill)
        torch.save(self.train_dataloader.dataloader, dataloader_local_path, pickle_module=dill)

        # latest checkpointed iteration tracker (for atomic usage)
        local_latest_checkpointed_iteration = os.path.join(self.config.trainer.default_local_dir,
                                                           'latest_checkpointed_iteration.txt')
        with open(local_latest_checkpointed_iteration, 'w') as f:
            f.write(str(self.global_steps))
        
        # after saving the checkpoint, we need to remove previous checkpoints
        try:
            cur_step = self.global_steps
            prev_save_steps = [i for i in range(0, cur_step, self.config.trainer.save_freq)]
            prev_save_steps = prev_save_steps[:-(self.config.trainer.max_optim_to_keep-1)]
            print(f'Removing optim in previous checkpoints: {prev_save_steps}')
            for each_save_step in prev_save_steps:
                prev_save_path = os.path.join(self.config.trainer.default_local_dir, f'global_step_{each_save_step}', 'actor')
                if not os.path.exists(prev_save_path):
                    continue
                # if exists, remove all optim.pt
                for path in os.listdir(prev_save_path):
                    if path.startswith('optim') and path.endswith('.pt'):
                        os.remove(os.path.join(prev_save_path, path))
                        print(f'Removed {os.path.join(prev_save_path, path)}')
        except Exception as e:
            print(f'Error removing previous checkpoints: {e}')
                

    def _load_checkpoint(self):
        if self.config.trainer.resume_mode == 'disable':
            return 0

        # load from hdfs
        if self.config.trainer.default_hdfs_dir is not None:
            NotImplementedError('load from hdfs is not implemented yet')
        else:
            checkpoint_folder = self.config.trainer.default_local_dir  # TODO: check path
            if not os.path.isabs(checkpoint_folder):
                working_dir = os.getcwd()
                checkpoint_folder = os.path.join(working_dir, checkpoint_folder)
            from verl.utils.checkpoint.checkpoint_manager import find_latest_ckpt_path
            global_step_folder = find_latest_ckpt_path(checkpoint_folder)  # None if no latest

        # find global_step_folder
        if self.config.trainer.resume_mode == 'auto':
            if global_step_folder is None:
                print('Training from scratch')
                return 0
        else:
            if not (self.config.trainer.resume_from_path and global_step_folder is not None):
                assert isinstance(self.config.trainer.resume_mode, str), "resume ckpt must be str type"
                assert 'global_step_' in self.config.trainer.resume_mode, "resume ckpt must specify the global_steps"
                global_step_folder = self.config.trainer.resume_mode
                if not os.path.isabs(global_step_folder):
                    working_dir = os.getcwd()
                    global_step_folder = os.path.join(working_dir, global_step_folder)
        print(f'Load from checkpoint folder: {global_step_folder}')
        # set global step
        self.global_steps = int(global_step_folder.split('global_step_')[-1])

        print(f'Setting global step to {self.global_steps}')
        print(f'Resuming from {global_step_folder}')

        actor_path = os.path.join(global_step_folder, 'actor')
        critic_path = os.path.join(global_step_folder, 'critic')
        # load actor
        self.actor_rollout_wg.load_checkpoint(actor_path)
        # load critic
        if self.use_critic:
            self.critic_wg.load_checkpoint(critic_path)

        # load dataloader,
        # TODO: from remote not implemented yet
        dataloader_local_path = os.path.join(global_step_folder, 'data.pt')
        train_dataloader = torch.load(dataloader_local_path)
        from .rl_dataset_with_target import BufferedDataLoader
        self.train_dataloader = BufferedDataLoader(train_dataloader)
        from verl.utils.dataset.rl_dataset import RLHFDataset
        if isinstance(self.train_dataloader.dataset, RLHFDataset):
            self.train_dataloader.dataset.resume_dataset_state()
