### prompt里标注现在日期，否则可能返回找不到2025-05月的结果
### workload太大有影响准确率，响应也很慢，建议改成5支股票
### client_session_timeout_seconds: 30 开大点否则会报错
### 验证：main.py 传入    
    Tickers = ["AAPL","TSLA","NVDA"] \ 
    start_date = "2025-06-30" \
    end_date = "2025-07-29" \
### 初始状态尽量把表格啥的都清空吧，否则agent发现表里有数据会重新从yahoo fetch数据
### 如果是最近两个月的数据好像会好一些，如果是5.6的数据会拉取很长的历史记录，也能跑就是很慢很长，导致我token用完了。。可酌情修改范围
```
到工具执行结果 google_sheet-list_sheets
assistant:  太好了！我发现第一个"2025_Q2_Market_Data"表格中已经有"May‑Jun_2025"这个Sheet了。现在让我获取AAPL、TSLA、NVDA、META这四只股票2025年5月和6月的历史行情数据：
>>调用工具 yahoo-finance-get_historical_stock_prices
[07/29/25 16:32:56] INFO     Processing request of type CallToolRequest                                                                                          server.py:534
>>收到工具执行结果 yahoo-finance-get_historical_stock_prices
assistant:  现在获取TSLA的数据：
>>调用工具 yahoo-finance-get_historical_stock_prices
[07/29/25 16:33:02] INFO     Processing request of type CallToolRequest                                                                                          server.py:534
>>收到工具执行结果 yahoo-finance-get_historical_stock_prices
assistant:  现在获取NVDA的数据：
>>调用工具 yahoo-finance-get_historical_stock_prices
[07/29/25 16:33:20] INFO     Processing request of type CallToolRequest                                                                                          server.py:534
>>收到工具执行结果 yahoo-finance-get_historical_stock_prices
assistant:  最后获取META的数据：
>>调用工具 yahoo-finance-get_historical_stock_prices
[07/29/25 16:33:40] INFO     Processing request of type CallToolRequest                                                                                          server.py:534
>>收到工具执行结果 yahoo-finance-get_historical_stock_prices
assistant:  现在我已经获取到了所有四只股票的历史数据。让我将2025年5月和6月的数据整理并更新到已存在的"May‑Jun_2025" Sheet中：
>>调用工具 google_sheet-get_sheet_data
Processing request of type CallToolRequest
>>收到工具执行结果 google_sheet-get_sheet_data
Context too long detected: 203016 tokens > 200000 maximum
Context too long detected: Context too long: current tokens in prompt = 203016 > maximum tokens =200000
Context reset after 9 executed steps, total: 9/20
Resetting context and history due to context too long error
assistant:  我看到之前的交互已经获取了所有四只股票的数据，并且发现已经存在"2025_Q2_Market_Data"表格和"May‑Jun_2025" Sheet。让我继续完成数据整理的任务。

首先让我检查当前Sheet中的数据结构，然后将2025年5月和6月的数据更新进去：
>>调用工具 google_sheet-get_sheet_data
Processing request of type CallToolRequest
>>收到工具执行结果 google_sheet-get_sheet_data
assistant:  我看到当前的Sheet中已经有一些数据了，但这些数据看起来是7月份的数据，而不是我们需要的5月和6月的数据。让我重新获取这四只股票2025年5月和6月的历史数据，然后清空现有数据并重新填入正确的数据。

首先，让我获取2025年5月和6月的数据：
>>调用工具 yahoo-finance-get_historical_stock_prices
[07/29/25 16:34:39] INFO     Processing request of type CallToolRequest                                                                                          server.py:534
>>收到工具执行结果 yahoo-finance-get_historical_stock_prices
assistant:  现在我需要从这些数据中提取2025年5月和6月的数据。让我处理这些数据，然后获取其他股票的数据。我将创建一个包含所有四只股票5月和6月数据的完整数据集，然后更新到Google Sheet中。

让我先获取其他三只股票的数据：
>>调用工具 yahoo-finance-get_historical_stock_prices
[07/29/25 16:35:00] INFO     Processing request of type CallToolRequest                                                                                          server.py:534
>>收到工具执行结果 yahoo-finance-get_historical_stock_prices
>>调用工具 yahoo-finance-get_historical_stock_prices
[07/29/25 16:35:22] INFO     Processing request of type CallToolRequest                                                                                          server.py:534
>>收到工具执行结果 yahoo-finance-get_historical_stock_prices
>>调用工具 yahoo-finance-get_historical_stock_prices
[07/29/25 16:35:50] INFO     Processing request of type CallToolRequest                                                                                          server.py:534
>>收到工具执行结果 yahoo-finance-get_historical_stock_prices
assistant:  现在我已经获取了所有四只股票的历史数据。我需要从这些数据中筛选出2025年5月和6月的数据，然后整理成合适的格式更新到Google Sheet中。让我创建一个包含所有相关数据的完整数据集：
```
