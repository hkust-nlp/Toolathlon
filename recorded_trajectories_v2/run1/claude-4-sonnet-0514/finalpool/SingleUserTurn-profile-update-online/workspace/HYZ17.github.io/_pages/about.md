---
permalink: /
title: ""
excerpt: "About me"
author_profile: true
redirect_from: 
  - /about/
  - /about.html
---

Hi, I am a second-year PhD student in [The Hong Kong University of Science and Technology](https://hkust.edu.hk), [Department of Computer Science and Engineering](https://cse.hkust.edu.hk). I am fortunate to be advised by Prof. [Junxian He](https://jxhe.github.io/). Before that, I received the bachelor degree in Computer Science in [Shanghai Jiao Tong University](https://en.sjtu.edu.cn/) in 2023. 

## Research Interests
I am primarily focused on large language models, particularly in advancing their reasoning capabilities and multimodal understanding. To achieve this, my research interests lie in: 
* Enhancing reasoning and planning abilities through self-improvement and RL techniques. (**B-STaR**, **SimpleRL**)
* Developing reliable evaluation methods for language models. (**C-Eval**, **LLM-Compression-Intelligence**)
* Improving the architecture and training methods of multimodal models to strengthen their understanding across multiple modalities.

I am open to any collaboration 🤗

## Publications
Most recent publications on [Google Scholar](https://scholar.google.com/citations?user=XZK8cewAAAAJ&hl=en).\\
\* denotes co-first authors

---
title: "SimpleRL-Zoo: Investigating and Taming Zero Reinforcement Learning for Open Base Models in the Wild"
collection: publications
permalink: /publication/2025-03-24-simplerl-zoo-zero-rl
excerpt: 'This work investigates zero RL training across 10 diverse base models, spanning different families and sizes, and shares key designs that enable successful zero RL training along with findings and practices for the research community.'
date: 2025-03-24
venue: 'arXiv preprint'
paperurl: 'https://arxiv.org/abs/2503.18892'
citation: 'Weihao Zeng, Yuzhen Huang, Qian Liu, Wei Liu, Keqing He, Zejun Ma, Junxian He. (2025). &quot;SimpleRL-Zoo: Investigating and Taming Zero Reinforcement Learning for Open Base Models in the Wild.&quot; <i>arXiv preprint arXiv:2503.18892</i>.'
---

<a href='https://arxiv.org/abs/2503.18892'>Download paper here</a>

* Investigate the linear correlation between compression and intelligence in LLMs.
* Provide evidence for the belief that superior compression is indicative of greater intelligence.
* Propose compression efficiency serves as an unsupervised and reliable metric to assess LLMs’ abilities.

DeepSeek-R1 has shown that long chain-of-thought (CoT) reasoning can naturally emerge through a simple reinforcement learning (RL) framework with rule-based rewards, where the training may directly start from the base models-a paradigm referred to as zero RL training. Most recent efforts to reproduce zero RL training have primarily focused on the Qwen2.5 model series, which may not be representative as we find the base models already exhibit strong instruction-following and self-reflection abilities. In this work, we investigate zero RL training across 10 diverse base models, spanning different families and sizes including LLama3-8B, Mistral-7B/24B, DeepSeek-Math-7B, Qwen2.5-math-7B, and all Qwen2.5 models from 0.5B to 32B. Leveraging several key design strategies-such as adjusting format reward and controlling query difficulty-we achieve substantial improvements in both reasoning accuracy and response length across most settings. However, by carefully monitoring the training dynamics, we observe that different base models exhibit distinct patterns during training. For instance, the increased response length does not always correlate with the emergence of certain cognitive behaviors such as verification (i.e., the "aha moment"). Notably, we observe the "aha moment" for the first time in small models not from the Qwen family. We share the key designs that enable successful zero RL training, along with our findings and practices. To facilitate further research, we open-source the code, models, and analysis tools.

Recommended citation: Weihao Zeng, Yuzhen Huang, Qian Liu, Wei Liu, Keqing He, Zejun Ma, Junxian He. (2025). "SimpleRL-Zoo: Investigating and Taming Zero Reinforcement Learning for Open Base Models in the Wild." <i>arXiv preprint arXiv:2503.18892</i>.

---
title: "B-STaR: Monitoring and Balancing Exploration and Exploitation in Self-Taught Reasoners"
collection: publications
permalink: /publication/2024-12-23-bstar-exploration-exploitation
excerpt: 'This paper identifies and proposes methods to monitor two pivotal factors in iterative self-improving methods: the model&apos;s ability to generate sufficiently diverse responses (exploration) and the effectiveness of external rewards in distinguishing high-quality candidates (exploitation).'
date: 2024-12-23
venue: 'ICLR 2025'
paperurl: 'https://arxiv.org/abs/2412.17256'
citation: 'Weihao Zeng, Yuzhen Huang, Lulu Zhao, Yijun Wang, Zifei Shan, Junxian He. (2024). &quot;B-STaR: Monitoring and Balancing Exploration and Exploitation in Self-Taught Reasoners.&quot; <i>ICLR 2025</i>.'
---
* Investigate the linear correlation between compression and intelligence in LLMs.
* Provide evidence for the belief that superior compression is indicative of greater intelligence.
* Propose compression efficiency serves as an unsupervised and reliable metric to assess LLMs’ abilities.

<a href='https://arxiv.org/abs/2412.17256'>Download paper here</a>

In the absence of extensive human-annotated data for complex reasoning tasks, self-improvement -- where models are trained on their own outputs -- has emerged as a primary method for enhancing performance. However, the critical factors underlying the mechanism of these iterative self-improving methods remain poorly understood, such as under what conditions self-improvement is effective, and what are the bottlenecks in the current iterations. In this work, we identify and propose methods to monitor two pivotal factors in this iterative process: (1) the model's ability to generate sufficiently diverse responses (exploration); and (2) the effectiveness of external rewards in distinguishing high-quality candidates from lower-quality ones (exploitation). Using mathematical reasoning as a case study, we begin with a quantitative analysis to track the dynamics of exploration and exploitation, discovering that a model's exploratory capabilities rapidly deteriorate over iterations, and the effectiveness of exploiting external rewards diminishes as well. Motivated by these findings, we introduce B-STaR, a Self-Taught Reasoning framework that autonomously adjusts configurations across iterations to Balance exploration and exploitation, thereby optimizing the self-improving effectiveness based on the current policy model and available rewards.

Recommended citation: Weihao Zeng, Yuzhen Huang, Lulu Zhao, Yijun Wang, Zifei Shan, Junxian He. (2024). "B-STaR: Monitoring and Balancing Exploration and Exploitation in Self-Taught Reasoners." <i>ICLR 2025</i>.

**Compression Represents Intelligence Linearly** \\
*<ins>Yuzhen Huang</ins>* \*, Jinghan Zhang *, Zifei Shan, Junxian He\\
COLM 2024. [[arxiv]](https://arxiv.org/abs/2404.09937) [[github]](https://github.com/hkust-nlp/llm-compression-intelligence) [[dataset]](https://huggingface.co/datasets/hkust-nlp/llm-compression)
* Investigate the linear correlation between compression and intelligence in LLMs.
* Provide evidence for the belief that superior compression is indicative of greater intelligence.
* Propose compression efficiency serves as an unsupervised and reliable metric to assess LLMs’ abilities.


**C-Eval: A Multi-Level Multi-Discipline Chinese Evaluation Suite for Foundation Models**\\
*<ins>Yuzhen Huang</ins>* \*, Yuzhuo Bai *, Zhihao Zhu, Junlei Zhang, Jinghan Zhang, Tangjun Su, Junteng Liu, Chuancheng Lv, Yikai Zhang, Jiayi Lei, Yao Fu, Maosong Sun, Junxian He\\
NeurIPS 2023 (Datasets and Benchmarks track). [[arxiv]](https://arxiv.org/abs/2305.08322) [[github]](https://github.com/hkust-nlp/ceval) [[website]](https://cevalbenchmark.com) [[dataset]](https://huggingface.co/datasets/ceval/ceval-exam)
* The first comprehensive Chinese evaluation suite for LLMs.
* Conduct a thorough evaluation of the most advanced LLMs.
* Over 9.8M downloads on Hugging Face and more than 100 models on leaderboard.



## Experiences
### Academia
- *2024.02 - now* PhD student, Department of CSE, [HKUST](https://hkust.edu.hk), Hong Kong SAR, China.
- *2019.09 - 2023.06* Undergraduate, Computer Science, [Shanghai Jiao Tong University](https://en.sjtu.edu.cn/), Shanghai, China.


## Service
Reviewer: NeurIPS 2024, ICLR 2025, ICML 2025, ARR

