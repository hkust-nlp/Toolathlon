.venv/lib/python3.12/site-packages/mcp_scholarly/google_scholar.py L14

please use the new 
```
    @staticmethod
    def _parse_results(search_results):
        articles = []
        results_iter = 0
        for searched_article in search_results:
            bib = searched_article.get('bib', {})
            title = bib.get('title', 'No title')
            abstract = bib.get('abstract', 'No abstract available')
            pub_url = searched_article.get('pub_url', 'No URL available')
            
            article_string = f"Title: {title}\nAbstract: {abstract}\nURL: {pub_url}"
            articles.append(article_string)
            results_iter += 1
            if results_iter >= MAX_RESULTS:
                break
        return articles
```
to replace the original one.