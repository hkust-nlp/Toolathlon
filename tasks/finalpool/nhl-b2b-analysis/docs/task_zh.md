分析NHL 2024-2025赛季每支球队的背靠背比赛分布，创建Google Sheet和本地CSV文件保存结果。

## 任务目标
分析NHL 2024-2025赛季的赛程数据，统计每支球队的背靠背比赛情况。

## 核心定义
**背靠背比赛**：同一支球队在连续两天都有比赛（比赛日期相差恰好1天）。

## 背靠背类型分类
1. **HA**：Home-Away（主场→客场）- 第一场主场，第二场客场
2. **AH**：Away-Home（客场→主场）- 第一场客场，第二场主场  
3. **HH**：Home-Home（主场→主场）- 两场都是主场
4. **AA**：Away-Away（客场→客场）- 两场都是客场
5. **Total**：该球队背靠背比赛的总次数（HA + AH + HH + AA）

## 输出要求

### 1. Google Sheets输出
- **表格名称**："背靠背比赛统计"
- **重要要求**：必须设置为公开可访问权限

### 2. 本地文件输出
- **文件名称**：nhl_b2b_analysis.csv
- **文件格式**：CSV格式，使用逗号分隔
- **表头格式**：Team,HA,AH,HH,AA,Total
- **保存位置**：任务工作区目录

## 数据源
**NHL赛程数据**：https://docs.google.com/spreadsheets/d/18Gpg5cauraSBIfrpn2VWbC7B2M999XpyPTVy3E29Pv8/edit?gid=1113684723#gid=1113684723




