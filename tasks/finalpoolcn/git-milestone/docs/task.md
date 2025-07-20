最近几天，GitHub的repo总数达到了1B，这是一个值得纪念的里程碑！我希望你能帮我搜集一些特殊的repo信息，记录这个历史性时刻。

我需要你收集以下几个里程碑式repo的信息：
- 第1个repo（repo ID: 1）
- 第1K个repo（repo ID: 1000）  
- 第1M个repo（repo ID: 1000000）
- 第1B个repo（repo ID: 1000000000）

请将这些信息保存到名字为github_info.json文件中。如果某个repo信息不存在或无法访问，请在输出json文件中跳过该repo。
格式为：
{
    "repo_id":{
        "key_0": "xxxx",
        "key_1": "xxxx"
    }
}

对于每个repo，请收集以下信息（在 json 文件中使用下面的key）:
- repo_name（仓库名称）
- owner（所有者用户名）
- star_count（星标数，整数值）
- fork_count（分叉数，整数值）
- creation_time（创建时间, ISO 8601 格式，带 Z 后缀，精确到秒）
- description（描述）
- language（主要编程语言）
- repo_url （仓库链接）

