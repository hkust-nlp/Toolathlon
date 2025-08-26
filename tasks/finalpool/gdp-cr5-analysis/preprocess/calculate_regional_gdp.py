#!/usr/bin/env python3
"""
根据世界银行七大区域划分统计各地区GDP总量
"""

import csv
import pandas as pd
from pathlib import Path
from create_region_mapping_from_pdf import get_world_bank_region_mapping

def clean_gdp_value(gdp_str):
    """
    清理GDP数值字符串，转换为数值
    """
    if not gdp_str or gdp_str.strip() == '-':
        return 0
    
    # 移除逗号、空格和引号
    cleaned = gdp_str.replace(',', '').replace(' ', '').replace('"', '').strip()
    
    try:
        return float(cleaned)
    except ValueError:
        print(f"无法解析GDP值: {gdp_str}")
        return 0

def load_gdp_data(csv_file_path):
    """
    从CSV文件加载GDP数据
    """
    gdp_data = {}
    
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            country_name = row['Country Name']
            gdp_value = clean_gdp_value(row['Economy (millions of US dollars)'])
            gdp_data[country_name] = gdp_value
    
    return gdp_data

def calculate_regional_gdp():
    """
    计算各地区GDP总量
    """
    # 获取地区映射
    region_mapping = get_world_bank_region_mapping()
    
    # 加载GDP数据
    csv_file = Path(__file__).parent / "GDP CR5 Analysis - Country.csv"
    gdp_data = load_gdp_data(csv_file)
    
    # 初始化各地区GDP总量
    regional_gdp = {
        "East Asia & Pacific": 0,
        "Europe & Central Asia": 0,
        "Latin America & Caribbean": 0,
        "Middle East & North Africa": 0,
        "North America": 0,
        "South Asia": 0,
        "Sub-Saharan Africa": 0
    }
    
    # 匹配的国家列表
    matched_countries = []
    unmatched_countries = []
    
    # 计算各地区GDP
    for country_name, gdp_value in gdp_data.items():
        if country_name in region_mapping:
            region = region_mapping[country_name]
            regional_gdp[region] += gdp_value
            matched_countries.append((country_name, region, gdp_value))
        else:
            unmatched_countries.append((country_name, gdp_value))
    
    return regional_gdp, matched_countries, unmatched_countries

def print_results():
    """
    打印统计结果
    """
    regional_gdp, matched_countries, unmatched_countries = calculate_regional_gdp()
    
    print("=" * 80)
    print("世界银行七大区域GDP统计 (2022年，百万美元)")
    print("=" * 80)
    
    # 计算全球总GDP
    total_global_gdp = sum(regional_gdp.values())
    
    # 按GDP从大到小排序
    sorted_regions = sorted(regional_gdp.items(), key=lambda x: x[1], reverse=True)
    
    for i, (region, gdp) in enumerate(sorted_regions, 1):
        percentage = (gdp / total_global_gdp) * 100 if total_global_gdp > 0 else 0
        print(f"{i}. {region}")
        print(f"   GDP: ${gdp:,.0f} 百万美元")
        print(f"   占全球比重: {percentage:.1f}%")
        print()
    
    print(f"全球GDP总计: ${total_global_gdp:,.0f} 百万美元")
    print(f"匹配国家数量: {len(matched_countries)}")
    print(f"未匹配国家数量: {len(unmatched_countries)}")
    
    if unmatched_countries:
        print("\n未匹配的国家/地区:")
        print("-" * 50)
        for country, gdp in unmatched_countries:
            if gdp > 0:  # 只显示有GDP数据的未匹配国家
                print(f"- {country}: ${gdp:,.0f} 百万美元")

def generate_detailed_report():
    """
    生成详细报告
    """
    regional_gdp, matched_countries, unmatched_countries = calculate_regional_gdp()
    
    print("\n" + "=" * 80)
    print("详细分地区国家列表")
    print("=" * 80)
    
    # 按地区分组显示
    region_countries = {}
    for country, region, gdp in matched_countries:
        if region not in region_countries:
            region_countries[region] = []
        region_countries[region].append((country, gdp))
    
    for region in sorted(region_countries.keys()):
        print(f"\n{region}:")
        print("-" * (len(region) + 1))
        countries = sorted(region_countries[region], key=lambda x: x[1], reverse=True)
        
        region_total = sum(gdp for _, gdp in countries)
        
        for country, gdp in countries:
            if gdp > 0:
                percentage = (gdp / region_total) * 100 if region_total > 0 else 0
                print(f"  {country}: ${gdp:,.0f} 百万美元 ({percentage:.1f}%)")
        
        print(f"  地区总计: ${region_total:,.0f} 百万美元")

def calculate_cr5_by_region():
    """
    计算各地区的CR5（前5大经济体集中度）
    """
    regional_gdp, matched_countries, unmatched_countries = calculate_regional_gdp()
    
    print("\n" + "=" * 80)
    print("各地区CR5分析（前5大经济体集中度）")
    print("=" * 80)
    
    # 按地区分组
    region_countries = {}
    for country, region, gdp in matched_countries:
        if region not in region_countries:
            region_countries[region] = []
        region_countries[region].append((country, gdp))
    
    for region in sorted(region_countries.keys()):
        countries = sorted(region_countries[region], key=lambda x: x[1], reverse=True)
        region_total = sum(gdp for _, gdp in countries if gdp > 0)
        
        if region_total > 0:
            # 取前5大经济体
            top5 = countries[:5]
            top5_total = sum(gdp for _, gdp in top5 if gdp > 0)
            cr5 = (top5_total / region_total) * 100
            
            print(f"\n{region}:")
            print(f"  地区总GDP: ${region_total:,.0f} 百万美元")
            print(f"  前5大经济体:")
            for i, (country, gdp) in enumerate(top5, 1):
                if gdp > 0:
                    share = (gdp / region_total) * 100
                    print(f"    {i}. {country}: ${gdp:,.0f} 百万美元 ({share:.1f}%)")
            print(f"  CR5指数: {cr5:.1f}%")

if __name__ == "__main__":
    print_results()
    generate_detailed_report()
    calculate_cr5_by_region() 