# Position calculation
prices = {
    'MSFT': 439.21, 'AAPL': 246.62, 'NVDA': 131.73, 'AMD': 122.16, 'GOOGL': 191.01, 'META': 608.97,
    '9988.HK': 82.53, '3690.HK': 157.30, '1810.HK': 30.20, '0700.HK': 398.72,
    '002594.SZ': 92.83, '601318.SS': 51.10, '603259.SS': 54.16, '300750.SZ': 261.75, '600519.SS': 1511.34
}

usd_hkd, usd_cny = 7.7716, 7.2854
us_per = 66666.67
hk_per = 75000.0
a_per = 60000.0

print("Stock Position Plan (Dec 19, 2024 Opening Prices)")
print("="*60)

# US Stocks
print("US STOCKS:")
us_stocks = [('Microsoft', 'MSFT'), ('Apple', 'AAPL'), ('NVIDIA', 'NVDA'), ('AMD', 'AMD'), ('Google', 'GOOGL'), ('Meta', 'META')]
for name, ticker in us_stocks:
    shares = int(us_per / prices[ticker])
    print(f"{name}: {shares} shares")

print("\nHONG KONG STOCKS:")
hk_stocks = [('Alibaba', '9988.HK'), ('Meituan', '3690.HK'), ('XIAOMI', '1810.HK'), ('Tencent', '0700.HK')]
for name, ticker in hk_stocks:
    price_usd = prices[ticker] / usd_hkd
    shares = int(hk_per / price_usd)
    print(f"{name}: {shares} shares")

print("\nA-SHARES:")
a_stocks = [('BYD', '002594.SZ'), ('Ping An Insurance', '601318.SS'), ('WuXi AppTec', '603259.SS'), ('CATL', '300750.SZ'), ('Moutai', '600519.SS')]
for name, ticker in a_stocks:
    price_usd = prices[ticker] / usd_cny
    shares_raw = int(a_per / price_usd)
    shares = max(100, (shares_raw // 100) * 100)
    print(f"{name}: {shares} shares")
