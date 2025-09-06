您好！我是一位从事深度学习研究的博士生。最近我和合作者提出了一个逻辑推理的数据集，并且正在撰写论文向社区介绍这个新的数据集。为了展示我们工作与之前工作的差异，我需要你帮我总结一个latex表格，并保存在工作空间下的 datasets.tex 中。表格中需要包含四列，Dataset（数据集名称）、Tasks（数据集中包含的任务数目）、Trainable（是否包含训练集，内容用\ding{55}或\ding{51}填充）、Adjustable Difficulty（是否包含不同难度，内容用\ding{55}或\ding{51}填充）。表格的格式如下：

```tex
\begin{table}[!ht]
    \begin{center}
    \begin{tabular}{lccc}
        \toprule
        Dataset & Tasks & Trainable & Adjustable Difficulty\\
        \midrule
        % content
        \bottomrule
    \end{tabular}
  \end{center}
\end{table}
```

需要整理的数据集名称为：
- BBH
- Zebra Logic
- KOR-Bench (任务数应基于论文中的大类划分)
- K&K (https://arxiv.org/abs/2410.23123)
- BBEH