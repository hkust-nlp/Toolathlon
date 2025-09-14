<div align="center">


<h1 style="display: flex; justify-content: center; align-items: center; gap: 10px; margin: 0;">
  <img src="./figures/logo.png" alt="LUFFY Icon" width="50">
  LUFFY: Learning to Reason Under Off‑Policy Guidance
</h1>
<p align="center"><em>A general framework for off-policy learning in large reasoning models.</em></p>

<div align="center">
  <img src="./figures/luffy_intro_new.jpg" alt="overview" style="width: 66%; height: auto;">
</div>


[![Paper](https://img.shields.io/badge/paper-A42C25?style=for-the-badge&logo=arxiv&logoColor=white)](http://arxiv.org/abs/2504.14945) [![alphaXiv](https://img.shields.io/badge/discussion-A42C25?style=for-the-badge&logo=arxiv&logoColor=white&color=blue
)](https://www.alphaxiv.org/abs/2504.14945) [![Github](https://img.shields.io/badge/LUFFY-000000?style=for-the-badge&logo=github&logoColor=000&logoColor=white)](https://github.com/ElliottYan/LUFFY)   [![Hugging Face Collection](https://img.shields.io/badge/LUFFY_Collection-fcd022?style=for-the-badge&logo=huggingface&logoColor=000)](https://huggingface.co/collections/Elliott/luffy-rl-6804e1f5d1ebe66ba8ac92f4) [![Twitter](https://img.shields.io/badge/Twitter-%23000000.svg?style=for-the-badge&logo=twitter&logoColor=white)](https://x.com/yafuly/status/1914559433549676962)





</div>

---

# 📚 Overview
- 🎉 [News](#news)  
- 📖 [Introduction](#introduction)  
- ✨ [Getting Started](#getting-started)  
- 🔧 [Usage](#usage)  
- 📃 [Evaluation](#evaluation)  
- 🎈 [Citation](#citation)  
- 🌻 [Acknowledgement](#acknowledgement)  
<!-- - 📈 [Star History](#star-history) -->


---


# 🎉News
- **[2025/05/30]** We integrate the implementation and scripts of **other off-policy learning methods** including SFT, SFT+RL and RL w/ SFT Loss (multi-task learning).
- **[2025/05/21]** We have updated the paper [version](https://arxiv.org/abs/2504.14945), which re-evaluates all models using a more accurate verifier and adds comparisons with other off-policy learning methods, including RL with SFT Loss and SFT+RL.
- **[2025/04/23]** Our paper now trending on [alphaXiv](https://www.alphaxiv.org/abs/2504.14945)! We welcome feedback and discussion.
- **[2025/04/23]** 🎉 Ranked **#1** of the day on [Huggingface Daily Papers](https://huggingface.co/papers/2504.14945).
- **[2025/04/20]** LUFFY paper available on [arXiv](http://arxiv.org/abs/2504.14945). 

<!-- - **[2025/04/20]** The models and datasets are released on [HuggingFace](https://huggingface.co/collections/Elliott/luffy-rl-6804e1f5d1ebe66ba8ac92f4).
- **[2025/04/20]** LUFFY codebase is released along with evaluation scripts. Try it out! -->

---

# 📖Introduction

LUFFY is a reinforcement learning framework that bridges the gap between zero-RL and imitation learning by incorporating off-policy reasoning traces into the training process. Built upon GRPO, LUFFY combines on-policy rollouts with off-policy demonstrations during advantage estimation and introduces **policy shaping** via regularized importance sampling to emphasize low-probability yet crucial actions.

![overview](./figures/luffy_performance.jpg)

### Key Highlights:
- **Off-Policy Guidance:** Seamlessly integrates external reasoning traces to bootstrap learning from stronger models.
- **Dynamic Balance:** Learns when to imitate and when to explore, adapting over the course of training.
- **Policy Shaping:** Emphasizes important actions often ignored in standard policy gradients, enabling better generalization.



---

# ✨Getting Started

## Installation

You can install LUFFY dependencies by running the following commands:
```bash
conda create -n luffy python=3.10
conda activate luffy
cd luffy
pip install -r requirements.txt
pip install -e .
cd verl
pip install -e .
```

If you encounter issues when installing flash-attn, we recommend you to install it here 
[flash-attn](https://github.com/Dao-AILab/flash-attention/releases/tag/v2.7.3). For example, we use this version. 
```bash
wget https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.3/flash_attn-2.7.3+cu12torch2.4cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
pip install flash_attn-2.7.3+cu12torch2.4cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
```

## Repo Structure

This repository includes:

- `luffy`: Codes for training LUFFY using off-policy reasoning traces. Our main code changes are in luffy/verl/verl/mix_src.
- `data`: Data and code for training and evaluating LUFFY. 
- `exp_scripts`: Example script to train LUFFY.
- `eval_scripts`: Evaluation scripts on math and out-of-distribution benchmarks.

LUFFY is built on top of the GRPO framework and supports plug-and-play integration with off-policy traces from models such as DeepSeek-R1.

---





# 🔧Usage

## Data Preparation
You need to first run the data preparation script to get the training data in parquet format.
```bash
cd data
python prepare_train.py
```

## Training

We provide an example script to train LUFFY on our subset of OpenR1-Math-220k. You can run the following command to train LUFFY:

```bash
  cd exp_scripts
  bash train.sh
```

## Other Off-Policy Baselines
### SFT
First clone the OpenRLHF repository and prepare the data to SFT format. *(We plan to integrate the SFT pipeline directly into LUFFY in the near future.)*
```bash
git clone https://github.com/OpenRLHF/OpenRLHF
cd data
python prepare_sft.py
```
Then, you can run the SFT training command. 
```
RESULT_DIR="Your result directory"
DATA_DIR="Your data directory"
WANDB_KEY="Your Wandb Key"

MODEL_PATH=Elliott/Qwen2.5-Math-7B-16k-think
MASTER_ADDR=`scontrol show hostname $SLURM_JOB_NODELIST | head -n1`
MASTER_PORT=$((RANDOM % 101 + 20000))
DEVICES="0,1,2,3,4,5,6,7"
deepspeed --master_port=$MASTER_PORT --master_addr=$MASTER_ADDR --include localhost:$DEVICES --module openrlhf.cli.train_sft \
   --max_len 16384 \
   --dataset $DATA_DIR \
   --input_key prompt \
   --output_key target \
   --train_batch_size 64 \
   --apply_chat_template \
   --micro_train_batch_size 1 \
   --max_samples 500000 \
   --pretrain $MODEL_PATH \
   --save_path $RESULT_DIR \
   --logging_steps 1 \
   --eval_steps -1 \
   --zero_stage 2 \
   --max_epochs 3 \
   --adam_offload \
   --packing_samples \
   --bf16 \
   --flash_attn \
   --save_hf_ckpt \
   --learning_rate 5e-5 \
   --lr_warmup_ratio 0.1 \
   --wandb_project r1_sft_distill \
   --wandb_run_name qwen-7b-base-sft \
   --use_wandb $WANDB_KEY \
   --gradient_checkpointing
```


### RL w/ SFT Loss
```bash
  cd exp_scripts
  bash train_rl_sft_loss.sh
```

### SFT + RL
We use heldout data for RL training, following previous works like PRIME.
```bash
  cd data
  python prepare_train_sft_rl.py
  cd ../exp_scripts
  bash train_sft_rl.sh
```

## Inference

Here’s an example of using LUFFY for inference:

<details>
<summary>Click to view inference example</summary>

```python
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams

model_path="Elliott/LUFFY-Qwen-Math-7B-Zero"

question = "which number is larger? 9.11 or 9.9?"

tokenizer = AutoTokenizer.from_pretrained(model_path)
messages = [{"role": "user", "content": question}]
chat = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

llm = LLM(model=model_path)
params = SamplingParams(temperature=0.6, max_tokens=8192)
outputs = llm.generate([chat], params)
print(outputs[0].outputs[0].text)
```

</details>


## Models

| **Model**                          | **Huggingface** |  **Base Model** |
|-----------------------------------|------------------|------------------|
| LUFFY-Qwen-Math-7B-Zero | https://huggingface.co/Elliott/LUFFY-Qwen-Math-7B-Zero |  Qwen2.5-Math-7B |
| LUFFY-Qwen-Math-7B-SFT | https://huggingface.co/Elliott/Qwen2.5-Math-7B-SFT | Qwen2.5-Math-7B |
| LUFFY-Qwen-Math-7B-SFT-RL | https://huggingface.co/Elliott/Qwen2.5-Math-7B-SFT-RL | Qwen2.5-Math-7B |
| LUFFY-Qwen-Math-1.5B-Zero | https://huggingface.co/Elliott/LUFFY-Qwen-Math-1.5B-Zero | Qwen2.5-Math-1.5B |
| LUFFY-Qwen-Instruct-7B | https://huggingface.co/Elliott/LUFFY-Qwen-Instruct-7B | Qwen2.5-7B-Instruct |

---

# 📃Evaluation

## Reproducing the Results 
We currently support automated evaluation on six widely used mathematical reasoning benchmarks (AIME24/25, AMC, MATH-500, Minerva, and Olympiad) and three out-of-distribution tasks (ARC-c, GPQA-diamond, and MMLU-pro). The platform provides specialized system prompts for a range of RL models, including LUFFY, SimpleRL, OpenReasoner, PRIME, and OAT.

You can reproduce our results by running the following commands:
```bash
ROOT=YOUR_ROOT_PATH
DATA=$ROOT/data/valid.all.parquet

OUTPUT_DIR=./results/
mkdir -p $OUTPUT_DIR

# If you want to evaluate other models, you can change the model path and name.
MODEL_PATH=Elliott/LUFFY-Qwen-Math-7B-Zero
MODEL_NAME=luffy

if [ $MODEL_NAME == "eurus-2-7b-prime-zero" ]; then
  TEMPLATE=prime
elif [ $MODEL_NAME == "simple-rl-zero" ]; then
  TEMPLATE=qwen
else
  TEMPLATE=own
fi

CUDA_VISIBLE_DEVICES=0,1,2,3 python eval_scripts/generate_vllm.py \
  --model_path $MODEL_PATH \
  --input_file $DATA \
  --remove_system True \
  --add_oat_evaluate True \
  --output_file $OUTPUT_DIR/$MODEL_NAME.jsonl \
  --template $TEMPLATE > $OUTPUT_DIR/$MODEL_NAME.log
```



## LUFFY on Qwen2.5-Math-7B (zero-RL)
LUFFY is evaluated on six competition-level benchmarks, achieving state-of-the-art results among all zero-RL methods. It surpasses both on-policy RL and imitation learning (SFT), especially in generalization:



| **Model**                          | **AIME 2024** | **AIME 2025** | **AMC** | **MATH-500** | **Minerva** | **Olympiad** | **Avg.** |
|-----------------------------------|-------------|-------------|---------|---------------|-------------|---------------|----------|
| Qwen2.5-Math-7B                      |11.5 | 4.9 | 31.3 | 43.6 | 7.4 | 15.6 | 19.0 |
| Qwen2.5-Math-7B-Instruct             |12.5  | 10.2 | 48.5 | 80.4 | 32.7 | 41.0 | 37.6   |
| SimpleRL-Zero                     | 27.0 | 6.8  | 54.9 | 76.0 | 25.0 | 34.7 | 37.4     |
| OpenReasoner-Zero                 | 16.5 | 15.0 | 52.1 | 82.4 | 33.1 | 47.1 | 41.0    |
| PRIME-Zero                        | 17.0 | 12.8 | 54.0 | 81.4 | **39.0** | 40.3 | 40.7    |
| Oat-Zero                          | **33.4**  | 11.9 | 61.2 | 78.0 | 34.6 | 43.4 | 43.7   |
| **LUFFY-Qwen-Math-7B-Zero**                         | 29.4        | **23.1**        | **65.6**| **87.6**      | 37.5        | **57.2**      | **50.1** |

---



LUFFY also generalizes well to out-of-distribution tasks, with over +6.2 average gain on ARC-C, GPQA, and MMLU-Pro.


| **Model**                         | **ARC-c** | **GPQA-diamond** | **MMLU-Pro** | **Avg.** |
|----------------------------------|-----------|------------------|--------------|----------|
| Qwen2.5-Math-7B             | 18.2 | 11.1 | 16.9 | 15.4  |
| Qwen2.5-Math-7B-Instruct         | 70.3 | 24.7 | 34.1 | 43.0    |
| SimpleRL-Zero                    | 30.2 | 23.2 | 34.5 | 29.3     |
| OpenReasoner-Zero                       | 66.2 | 29.8 | 58.7 | 51.6     |
| PRIME-Zero                         | 73.3 | 18.2 | 32.7 | 41.4   |
| Oat-Zero                | 70.1 | 23.7 | 41.7 | 45.2    |
| **LUFFY-Qwen-Math-7B-Zero**                        | **80.5** |  **39.9** | **53.0** | **57.8** |


We further compare LUFFY with alternative off-policy learning methods, including SFT, RL w/ SFT Loss and SFT+RL (see our paper for details):

| **Model**                          | **GPU Hours** | **Data Usage (On/Off)** | **AIME 2024** | **AIME 2025** | **AMC** | **MATH-500** | **Minerva** | **Olympiad** | **Avg.** |
|-----------------------------------|-------------|-------------|-------------|-------------|---------|---------------|-------------|---------------|----------|
| SFT                      | 24*8 | 0 / 64k | 22.2 | 22.3 | 52.8 | 82.6 | 40.8 | 43.7 | 44.1 |
| RL w/ SFT Loss             |  133*8    | 64k*7 / 64k  |  19.5 | 16.4 | 49.7 | 80.4 | 34.9 | 39.4 | 40.1  |
| SFT+RL                      | 130*8 |  64k*8/135k |  25.8 | **23.1** | 62.7 | 87.2 | 39.7 | 50.4 | 48.2 |
| **LUFFY-Qwen-Math-7B-Zero**            | 77*8 | 64k*7 / 64k              | 29.4        | **23.1**        | 65.6 | **87.6**      | 37.5        | **57.2**      | 50.1 |
| **LUFFY-Qwen-Math-7B-Zero-Extra**       |    130*8       |   110k*7 / 110k      | **30.7** | 22.5 | **66.2**|  86.8 | **41.2** | 55.3 | **50.4** |

---

## LUFFY on Qwen2.5-Math-1.5B
| **Model**                          | **AIME 2024** | **AIME 2025** | **AMC** | **MATH-500** | **Minerva** | **Olympiad** | **Avg.** |
|-----------------------------------|-------------|-------------|---------|---------------|-------------|---------------|----------|
| Qwen2.5-Math-1.5B                  |   7.2 |  3.6 | 26.4 | 28.0 | 9.6 | 21.2 | 16.0 |
| Qwen2.5-Math-1.5B-Instruct            |  12.1 | 8.9 | 48.1 | 77.4 | 28.7 | 39.1 | 35.7 |
| **LUFFY-Qwen-Math-1.5B-Zero**             | **16.0** | **13.1** | **47.1** | **80.2** | **30.5** | **41.0** | **38.0** |



## LUFFY on Qwen2.5-Instruct-7B 
| **Model**                          | **AIME 2024** | **AIME 2025** | **AMC** | **MATH-500** | **Minerva** | **Olympiad** | **Avg.** |
|-----------------------------------|-------------|-------------|---------|---------------|-------------|---------------|----------|
| Qwen2.5-7B-Instruct           | 11.7 | 7.5 | 43.8 | 71.8 | 30.9 | 40.4|  34.4|
| **LUFFY-Qwen-Instruct-7B**             | **17.7** |  **14.8** | **50.9** | **82.0** | **31.3** | **47.4** | **40.7** |


# 🌻Acknowledgement

LUFFY builds upon [veRL](https://github.com/volcengine/verl) and [deepscaler](https://github.com/agentica-project/rllm), and utilizes [vLLM](https://github.com/vllm-project/vllm) for inference. We utilize [Math-Verify](https://github.com/huggingface/Math-Verify) for math reasoning evaluation. We thank the open-source community for datasets and backbones, including [NuminaMath](https://huggingface.co/datasets/AI-MO/NuminaMath-CoT), [OpenR1-Math-220k](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k), [Qwen2.5-Math](https://github.com/QwenLM/Qwen2.5-Math), and [DeepSeek-R1](https://github.com/deepseek-ai/deepseek-r1) model. 

# 📬 Contact

For questions, feedback, or collaboration opportunities, feel free to reach out:
- Jianhao Yan: elliottyan37@gmail.com
- Yafu Li: yafuly@gmail.com

# Citation
If you find our model, data, or evaluation code useful, please kindly cite our paper:
```bib
@misc{luffy,
      title={Learning to Reason under Off-Policy Guidance}, 
      author={Jianhao Yan and Yafu Li and Zican Hu and Zhi Wang and Ganqu Cui and Xiaoye Qu and Yu Cheng and Yue Zhang},
      year={2025},
      eprint={2504.14945},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2504.14945}, 
}
```

