1. You could check the groundtruth calculation details in `Calculation Process.xlsx`
2. Always meet some error report like: 
    INFO     Processing request of type CallToolRequest                                                                                              server.py:551
                        ERROR    HTTP Error 404:                                                                                                                          quote.py:592
    [09/15/25 18:00:52] ERROR    $TRYCNY=X: possibly delisted; no timezone found 
3. For claude-4-sonnet-0514, it always mix up the EUR and TRY and fail to calculate the amount.