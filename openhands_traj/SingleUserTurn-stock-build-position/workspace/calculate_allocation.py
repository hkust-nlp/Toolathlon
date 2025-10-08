# Stock categorization and ticker mapping
stocks_data = {
    # US Stocks
    'Microsoft': {'ticker': 'MSFT', 'market': 'US'},
    'Apple': {'ticker': 'AAPL', 'market': 'US'},
    'NVIDIA': {'ticker': 'NVDA', 'market': 'US'},
    'AMD': {'ticker': 'AMD', 'market': 'US'},
    'Google': {'ticker': 'GOOGL', 'market': 'US'},
    'Meta': {'ticker': 'META', 'market': 'US'},
    
    # Hong Kong Stocks
    'Alibaba': {'ticker': '9988.HK', 'market': 'HK'},
    'Meituan': {'ticker': '3690.HK', 'market': 'HK'},
    'XIAOMI': {'ticker': '1810.HK', 'market': 'HK'},
    'Tencent': {'ticker': '0700.HK', 'market': 'HK'},
    
    # A-shares
    'BYD': {'ticker': '002594.SZ', 'market': 'A'},
    'Ping An Insurance': {'ticker': '601318.SS', 'market': 'A'},
    'WuXi AppTec': {'ticker': '603259.SS', 'market': 'A'},
    'CATL': {'ticker': '300750.SZ', 'market': 'A'},
    'Moutai': {'ticker': '600519.SS', 'market': 'A'},
}

total_capital = 1000000
us_allocation = total_capital * 0.4
hk_allocation = total_capital * 0.3
a_allocation = total_capital * 0.3

us_count = sum(1 for info in stocks_data.values() if info['market'] == 'US')
hk_count = sum(1 for info in stocks_data.values() if info['market'] == 'HK')
a_count = sum(1 for info in stocks_data.values() if info['market'] == 'A')

print("US Stocks:", us_count)
print("HK Stocks:", hk_count)
print("A-shares:", a_count)
print("US allocation per stock:", us_allocation/us_count)
print("HK allocation per stock:", hk_allocation/hk_count)
print("A allocation per stock:", a_allocation/a_count)
