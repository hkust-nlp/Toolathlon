请帮我为一位目前居住在洛杉矶加州的学生准备研究生申请报告，该学生希望就读就近大学以便能够定期回家。请帮我查找洛杉矶县自然历史博物馆500英里范围内，所有2024年的CS Ranking AI 领域（排除信息检索）排名前30的学校的详细信息。

对于每个符合距离要求的项目，请收集：1）英文大学全名、英文城市名和排名；2）从洛杉矶县自然历史博物馆开车的最短距离（以英里为单位，仅保留整数）；请将信息保存为'AI_univ_LA_500miles_Top30_2024.json'，格式如下，按距离从近到远排序大学，距离相同时排名高者列前： 

[
    {
        "university":"{name}",
        "city":"{city}",
        "cs_ranking_rank":{rank},
        "car_drive_miles":{miles}
    },
    {
        "university":"{name}",
        "city":"{city}",
        "cs_ranking_rank":{rank},
        "car_drive_miles":{miles}
    },
    ...
]
