你好！我是一名从事深度学习研究的博士生。最近，我和合作者提出了一个逻辑推理数据集，正在撰写论文向学术界介绍这个新数据集。为了展示我们的工作与前人工作的区别，我需要你帮我总结一个latex表格，并将其保存在工作区中，文件名为datasets.tex，该tex文件应该只包含表格内容（不要出现被注释的行），不包含其他内容。表格需要包含四列：Dataset（数据集名称）、Tasks（数据集包含的任务数量）、Trainable（是否包含训练集，用\ding{55}或\ding{51}填充）、Adjustable Difficulty（是否包含不同难度级别，用\ding{55}或\ding{51}填充）。表格格式如下：

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

需要整理的数据集名称为（从上至下）：
- BBH
- Zebra Logic
- KOR-Bench (任务数应基于论文中的大类划分)
- K&K (https://arxiv.org/abs/2410.23123)
- BBEH