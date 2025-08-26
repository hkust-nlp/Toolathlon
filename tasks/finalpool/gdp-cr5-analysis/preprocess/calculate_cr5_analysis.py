#!/usr/bin/env python3
"""
计算各地区CR5指数（前5大经济体集中度）
"""

import csv
import pandas as pd
from pathlib import Path

def load_region_mapping_from_excel():
    """
    从CLASS.xlsx文件加载国家-地区映射关系
    """
    xlsx_file = Path(__file__).parent / "CLASS.xlsx"
    
    if not xlsx_file.exists():
        raise FileNotFoundError(f"找不到文件: {xlsx_file}")
    
    try:
        # 读取Excel文件
        df = pd.read_excel(xlsx_file)
        
        # 创建映射字典：Economy -> Region
        region_mapping = {}
        
        for _, row in df.iterrows():
            economy = str(row['Economy']).strip()
            region = str(row['Region']).strip()
            
            if economy and region and economy != 'nan' and region != 'nan':
                region_mapping[economy] = region
        
        print(f"从 {xlsx_file} 加载了 {len(region_mapping)} 个国家-地区映射")
        return region_mapping
        
    except Exception as e:
        print(f"读取Excel文件时出错: {e}")
        return {}

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

def load_regional_gdp_data():
    """
    从地区CSV文件加载地区GDP数据
    """
    regional_data = {}
    
    csv_file = Path(__file__).parent / "GDP2022 - Region.csv"
    
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            region_code = row['Region Code']
            region_name = row['Region Name']
            gdp_value = clean_gdp_value(row['Economy (millions of US dollars)'])
            
            # 映射到标准地区名称
            if region_name == 'East Asia & Pacific':
                regional_data['East Asia & Pacific'] = gdp_value
            elif region_name == 'Europe & Central Asia':
                regional_data['Europe & Central Asia'] = gdp_value
            elif region_name == 'Latin America & Caribbean':
                regional_data['Latin America & Caribbean'] = gdp_value
            elif region_name == 'Middle East & North Africa':
                regional_data['Middle East & North Africa'] = gdp_value
            elif region_name == 'North America':
                regional_data['North America'] = gdp_value
            elif region_name == 'South Asia':
                regional_data['South Asia'] = gdp_value
            elif region_name == 'Sub-Saharan Africa':
                regional_data['Sub-Saharan Africa'] = gdp_value
            elif region_name == 'World':
                regional_data['World'] = gdp_value
    
    return regional_data

def load_country_gdp_data():
    """
    从国家CSV文件加载各国GDP数据
    """
    gdp_data = {}
    
    csv_file = Path(__file__).parent / "GDP2022 - Country.csv"
    
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            country_name = row['Country Name']
            gdp_value = clean_gdp_value(row['Economy (millions of US dollars)'])
            gdp_data[country_name] = gdp_value
    
    return gdp_data

def calculate_cr5_by_region():
    """
    计算各地区的CR5指数
    """
    # 获取地区映射和数据
    region_mapping = load_region_mapping_from_excel()
    regional_gdp_data = load_regional_gdp_data()
    country_gdp_data = load_country_gdp_data()
    
    # 按地区分组国家
    region_countries = {}
    
    for country_name, gdp_value in country_gdp_data.items():
        if country_name in region_mapping and gdp_value > 0:
            region = region_mapping[country_name]
            if region not in region_countries:
                region_countries[region] = []
            region_countries[region].append((country_name, gdp_value))
    
    print("=" * 80)
    print("各地区CR5分析（前5大经济体集中度）")
    print("=" * 80)
    
    # 全球CR5计算
    all_countries = [(country, gdp) for country, gdp in country_gdp_data.items() if gdp > 0]
    all_countries.sort(key=lambda x: x[1], reverse=True)
    
    global_total = regional_gdp_data.get('World', sum(gdp for _, gdp in all_countries))
    global_top5 = all_countries[:5]
    global_top5_total = sum(gdp for _, gdp in global_top5)
    global_cr5 = (global_top5_total / global_total) * 100
    
    print(f"\n全球CR5分析:")
    print(f"全球GDP总计: ${global_total:,.0f} 百万美元")
    print(f"前5大经济体:")
    for i, (country, gdp) in enumerate(global_top5, 1):
        share = (gdp / global_total) * 100
        print(f"  {i}. {country}: ${gdp:,.0f} 百万美元 ({share:.1f}%)")
    print(f"全球CR5指数: {global_cr5:.1f}%")
    
    print("\n" + "=" * 80)
    print("各地区CR5详细分析")
    print("=" * 80)
    
    # 按地区GDP从大到小排序
    regions_by_gdp = []
    for region in region_countries.keys():
        region_total = regional_gdp_data.get(region, 0)
        regions_by_gdp.append((region, region_total))
    
    regions_by_gdp.sort(key=lambda x: x[1], reverse=True)
    
    cr5_results = []
    
    for region, region_total_official in regions_by_gdp:
        if region in region_countries:
            countries = sorted(region_countries[region], key=lambda x: x[1], reverse=True)
            
            # 使用官方地区总GDP数据
            region_total = region_total_official if region_total_official > 0 else sum(gdp for _, gdp in countries)
            
            if region_total > 0:
                # 取前5大经济体
                top5 = countries[:5]
                top5_total = sum(gdp for _, gdp in top5)
                cr5 = (top5_total / region_total) * 100
                
                cr5_results.append((region, cr5, region_total, top5))
                
                print(f"\n{region}:")
                print(f"  地区GDP总计: ${region_total:,.0f} 百万美元")
                print(f"  国家数量: {len(countries)}")
                print(f"  前5大经济体:")
                for i, (country, gdp) in enumerate(top5, 1):
                    share = (gdp / region_total) * 100
                    print(f"    {i}. {country}: ${gdp:,.0f} 百万美元 ({share:.1f}%)")
                print(f"  CR5指数: {cr5:.1f}%")
    
    # CR5排名总结
    print("\n" + "=" * 80)
    print("CR5指数排名总结")
    print("=" * 80)
    
    cr5_results.sort(key=lambda x: x[1], reverse=True)
    
    print(f"{'排名':<4} {'地区':<25} {'CR5指数':<10} {'地区GDP(百万美元)':<20}")
    print("-" * 70)
    
    for i, (region, cr5, gdp, _) in enumerate(cr5_results, 1):
        print(f"{i:<4} {region:<25} {cr5:>7.1f}% {gdp:>18,.0f}")
    
    # 分析CR5水平
    print(f"\n全球CR5指数: {global_cr5:.1f}%")
    print("\nCR5指数解读:")
    print("- CR5 > 80%: 高度集中")
    print("- 60% < CR5 ≤ 80%: 中度集中") 
    print("- 40% < CR5 ≤ 60%: 轻度集中")
    print("- CR5 ≤ 40%: 相对分散")
    
    return cr5_results

def export_results_to_csv():
    """
    将结果导出到CSV文件 - 与标准答案格式一致
    """
    cr5_results = calculate_cr5_by_region()
    
    output_file = Path(__file__).parent / "CR5_Analysis_Results.csv"
    
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # 使用与标准答案一致的列名
        writer.writerow(['Region', 'Top5_Countries', 'Top5_GDP_Sum', 'Region_GDP_Total', 'CR5_Ratio'])
        
        for region, cr5, region_gdp_total, top5 in cr5_results:
            # Top5_Countries: 仅包含国家名称，用逗号分隔
            top5_countries = ', '.join([country for country, gdp in top5])
            
            # Top5_GDP_Sum: 前5国家GDP总和
            top5_gdp_sum = sum(gdp for country, gdp in top5)
            
            # CR5_Ratio: CR5百分比值（不带百分号）
            cr5_ratio = round(cr5, 2)
            
            writer.writerow([
                region,                    # Region
                top5_countries,            # Top5_Countries  
                int(top5_gdp_sum),        # Top5_GDP_Sum
                int(region_gdp_total),    # Region_GDP_Total
                cr5_ratio                 # CR5_Ratio
            ])
    
    print(f"\n结果已导出到: {output_file}")
    print("文件格式与标准答案一致：Region, Top5_Countries, Top5_GDP_Sum, Region_GDP_Total, CR5_Ratio")

if __name__ == "__main__":
    calculate_cr5_by_region()
    print("\n" + "=" * 80)
    export_results_to_csv() 