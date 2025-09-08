有人刚在我的Annoy-DataSync项目里提了个issue想知道我们发布的数据集的许可证信息，你能帮我看一下我们应该用什么许可证吗？我的要求就是直接复用数据集的直接数据源或合成用到的模型的许可证，若有多个来源则选用其中对衍生/二次使用最宽松的一个。完成判断后请你帮我回复并关闭这个issue，严格按照如下格式(除了占位符不要修改增减或修改其他内容)：

"Thanks for your interest! The licenses of the two datasets are: Annoy-PyEdu-Rs-Raw = {license}, Annoy-PyEdu-Rs = {license}"

此外在对应的数据集页面也要更新一下，在原有的readme末尾处加上如下内容，此外不用加其他内容：
"\n\n**License**\n\nThe license for this dataset is {license}."

如果你需要huggingface token，你可以在.hf_token文件下找到它。