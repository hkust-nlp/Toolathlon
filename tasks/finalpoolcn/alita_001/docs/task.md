在 arXiv 上检索所有标题包含 "Alita" 的论文，要求发布日期在2025年6月或以前，全部筛选出来。将找到的论文 PDF 文件都下载到本地。分别读取这些论文的内容，判断哪一篇与 "agentic reasoning" 的关系更大，并说明理由。对于你认为与 "agentic reasoning" 关系更大的那一篇，请帮我在论文的摘要或正文中找到对应的 GitHub 仓库链接（repo url），并记录下来。

最终，请以json结构化的格式输出以下内容：所有论文的完整标题、arXiv 分类、哪一篇相关性更高、该论文的 GitHub repo 链接和 arXiv 页面链接。请将结果保存为 result.json 文件。

请严格按照以下JSON格式输出：
```json
{
    "papers": [
        {
            "title": "论文完整标题",
            "arxiv_id": "arxiv ID（不包含版本号）",
            "arxiv_url": "https://arxiv.org/abs/{arxiv_id}",
            "category": "arXiv分类",
            "relevance_to_agentic_reasoning": "与agentic reasoning的相关性描述"
        }
    ],
    "most_relevant_paper": {
        "title": "最相关论文的标题",
        "reason": "详细的选择理由",
        "github_repo": "GitHub仓库链接"
    },
    "analysis_summary": "整体分析总结"
}
```

注意事项：
1. 必须包含所有找到的相关论文
2. arxiv_id不包含版本号（如v1、v2等）
3. arxiv_url格式为 https://arxiv.org/abs/{arxiv_id}
4. category使用arXiv官方分类标识
5. most_relevant_paper的title必须与papers中某篇论文的title完全一致
6. reason字段需要详细说明选择理由
7. github_repo必须是有效的GitHub仓库链接 