# Verl Dataset

ID: 146

## Evaluation

### Log

理论上模型会在log中输出一个`org/dataset`格式的数据集名称，因此我会验证正确的组织名`agentica-org`是否存在。

### Local

1. 检查目标数据集`verl_deepscaler.parquet`是否在工作空间下存在
2. 检查数据集中的条数是否正确
3. 检查各个属性是否存在，确保格式正确

个人觉得没有必要依次对照question和answer是否匹配。

## 可能的问题
- huggingface server在我的测试环境下（组内服务器）有时候连接不上
- 在提供了googlesearch这个server的前提下，即使连接不上HF Server模型也可以做对