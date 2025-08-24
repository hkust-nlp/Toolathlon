# Pricing data for iPad Pro 256GB 11-inch + Apple Pencil Pro with education discounts

pricing_data = {
    "United States": {
        "ipad_pro_256gb": 899,  # USD
        "apple_pencil_pro": 119,  # USD
        "currency": "USD"
    },
    "Hong Kong": {
        "ipad_pro_256gb": 7199,  # HKD
        "apple_pencil_pro": 899,  # HKD
        "currency": "HKD"
    },
    "Singapore": {
        "ipad_pro_256gb": 1349,  # SGD
        "apple_pencil_pro": 179,  # SGD
        "currency": "SGD"
    },
    "Mainland China": {
        "ipad_pro_256gb": 8099,  # RMB/CNY
        "apple_pencil_pro": 899,  # RMB/CNY
        "currency": "CNY"
    }
}

# Calculate total prices for each region
total_prices = {}
for region, prices in pricing_data.items():
    total = prices["ipad_pro_256gb"] + prices["apple_pencil_pro"]
    total_prices[region] = {
        "total": total,
        "currency": prices["currency"],
        "breakdown": {
            "ipad_pro_256gb": prices["ipad_pro_256gb"],
            "apple_pencil_pro": prices["apple_pencil_pro"]
        }
    }

# Display all prices
print("iPad Pro 256GB 11-inch + Apple Pencil Pro with Education Discounts:")
print("=" * 70)
for region, data in total_prices.items():
    currency = data["currency"]
    total = data["total"]
    ipad_price = data["breakdown"]["ipad_pro_256gb"]
    pencil_price = data["breakdown"]["apple_pencil_pro"]
    
    print(f"{region}:")
    print(f"  iPad Pro 256GB: {currency} {ipad_price:,}")
    print(f"  Apple Pencil Pro: {currency} {pencil_price:,}")
    print(f"  Total: {currency} {total:,}")
    print()

# Convert all prices to USD for comparison (approximate exchange rates as of late 2024)
exchange_rates = {
    "USD": 1.0,
    "HKD": 0.128,  # 1 HKD = ~0.128 USD
    "SGD": 0.74,   # 1 SGD = ~0.74 USD
    "CNY": 0.138   # 1 CNY = ~0.138 USD
}

usd_prices = {}
for region, data in total_prices.items():
    currency = data["currency"]
    total_local = data["total"]
    total_usd = total_local * exchange_rates[currency]
    usd_prices[region] = {
        "total_local": total_local,
        "total_usd": total_usd,
        "currency": currency
    }

# Find the cheapest option
cheapest_region = min(usd_prices.keys(), key=lambda x: usd_prices[x]["total_usd"])
cheapest_price_usd = usd_prices[cheapest_region]["total_usd"]
cheapest_price_local = usd_prices[cheapest_region]["total_local"]
cheapest_currency = usd_prices[cheapest_region]["currency"]

print("Price Comparison (converted to USD for comparison):")
print("=" * 50)
for region, data in usd_prices.items():
    local_price = data["total_local"]
    usd_price = data["total_usd"]
    currency = data["currency"]
    print(f"{region}: {currency} {local_price:,} (~USD {usd_price:.2f})")

print(f"\nCheapest Option: {cheapest_region}")
print(f"Price: {cheapest_currency} {cheapest_price_local:,} (~USD {cheapest_price_usd:.2f})")

# Prepare result for JSON file
result = {
    "cheapest_region": cheapest_region,
    "cheapest_total_price": f"{cheapest_currency} {cheapest_price_local:,}"
}

print(f"\nResult for JSON: {result}")