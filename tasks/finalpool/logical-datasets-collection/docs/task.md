Hello! I am a PhD student engaged in deep learning research. Recently, my collaborators and I have proposed a logical reasoning dataset and are writing a paper to introduce this new dataset to the community. To demonstrate the differences between our work and previous work, I need you to help me summarize a latex table and save it in the workspace with name as `datasets.tex`, the tex file should only contain table content (no commented lines), without any other content. The table needs to include four columns: Dataset (dataset name), Tasks (number of tasks included in the dataset), Trainable (whether it includes a training set, filled with \ding{55} or \ding{51}), and Adjustable Difficulty (whether it includes different difficulty levels, filled with \ding{55} or \ding{51}). The table format is as follows:

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

The names of the datasets we need to include are (from top to bottom):
- BBH
- Zebra Logic
- KOR-Bench (# of tasks should based the broader categorization in the paper.)
- K&K (https://arxiv.org/abs/2410.23123)
- BBEH