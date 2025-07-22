#!/usr/bin/env python3
import sys
import os
import pandas as pd

def compare_excel_files(file1, file2):
    REQUIRED_COLUMNS = ['课程名称', '课程代码', '任课老师', '上课校区', '上课时间', '学分数','考核方式','考试时间','开课院系','选课限制专业']
    
    try:
        if not os.path.exists(file1):
            return False, f"文件不存在: {file1}"
        if not os.path.exists(file2):
            return False, f"文件不存在: {file2}"
        
        df1 = pd.read_excel(file1)
        df2 = pd.read_excel(file2)
        
        available_cols = [col for col in REQUIRED_COLUMNS if col in df1.columns and col in df2.columns]
        if not available_cols:
            return False, f"未找到共同必需列: {REQUIRED_COLUMNS}"
        
        # 提取需要的列
        subset1 = df1[available_cols].copy()
        subset2 = df2[available_cols].copy()
        
        # 去除空行和无效数据
        def clean_dataframe(df, cols):
            """清理DataFrame，去除空行和无效数据"""
            # 去除所有指定列都为空的行
            df_clean = df.dropna(how='all', subset=cols)
            
            # 去除任一指定列为空或仅包含空字符串的行
            for col in cols:
                mask = df_clean[col].apply(lambda x: str(x).strip() != '' and not pd.isna(x))
                df_clean = df_clean[mask]
            
            # 重置索引
            return df_clean.reset_index(drop=True)
        
        # 清理数据
        subset1 = clean_dataframe(subset1, available_cols)
        subset2 = clean_dataframe(subset2, available_cols)
        
        # 显示数据概览
        print(f"\n文件1数据概览（清理后）:")
        print(subset1.head())
        print(f"\n文件2数据概览（清理后）:")
        print(subset2.head())
        
        # 检查数据条数
        print(f"\n文件1有效数据条数: {len(subset1)}")
        print(f"文件2有效数据条数: {len(subset2)}")
        
        sorted1 = subset1.sort_values(by=available_cols).reset_index(drop=True)
        sorted2 = subset2.sort_values(by=available_cols).reset_index(drop=True)
        
        if len(sorted1) != len(sorted2):
            return False, f"数据条数不匹配: {len(sorted1)} vs {len(sorted2)}"
        
        # 智能比较函数
        def smart_compare(val1, val2):
            """智能比较两个值，处理数值类型和字符串类型"""
            # 处理NaN值
            if pd.isna(val1) and pd.isna(val2):
                return True
            if pd.isna(val1) or pd.isna(val2):
                return False
            
            # 尝试数值比较
            try:
                num1 = float(str(val1).strip())
                num2 = float(str(val2).strip())
                # 使用小误差比较
                return abs(num1 - num2) < 1e-10
            except (ValueError, TypeError):
                # 如果不是数值，进行字符串比较
                str1 = ' '.join(str(val1).strip().split()).lower()
                str2 = ' '.join(str(val2).strip().split()).lower()
                return str1 == str2
        
        mismatches = []
        for i in range(len(sorted1)):
            for col in available_cols:
                val1 = sorted1.iloc[i][col]
                val2 = sorted2.iloc[i][col]
                
                if not smart_compare(val1, val2):
                    mismatches.append((i+1, col, str(val1), str(val2)))
        
        if mismatches:
            msg = f"发现 {len(mismatches)} 处不匹配:\n"
            for row, col, v1, v2 in mismatches[:5]:
                msg += f"  第{row}行 {col}: '{v1}' vs '{v2}'\n"
            return False, msg
        
        return True, f"匹配成功，共 {len(sorted1)} 条记录"
        
    except Exception as e:
        return False, f"错误: {str(e)}"

def main():
    if len(sys.argv) != 3:
        print("用法: python test_compare.py <文件1.xlsx> <文件2.xlsx>")
        sys.exit(1)
    
    file1, file2 = sys.argv[1], sys.argv[2]
    
    success, message = compare_excel_files(file1, file2)
    print("=" * 50)
    print("✅ 成功" if success else "❌ 失败")
    print("=" * 50)
    print(message)

if __name__ == "__main__":
    main() 