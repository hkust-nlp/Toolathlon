from argparse import ArgumentParser
import pandas as pd
import os

def check_local(agent_workspace: str, groundtruth_workspace: str):
    """
    主评估函数，被main.py调用
    """
    try:
        agent_file = os.path.join(agent_workspace, "Processed.xlsx")
        groundtruth_file = os.path.join(groundtruth_workspace, "Processed.xlsx")

        # 检查agent是否创建了Processed.xlsx文件
        if not os.path.exists(agent_file):
            return False, f"Agent workspace file not found: {agent_file}"

        if not os.path.exists(groundtruth_file):
            return False, f"Groundtruth file not found: {groundtruth_file}"

        # 读取agent生成的文件
        agent_df = pd.read_excel(agent_file)
        
        # 读取预期的groundtruth文件
        expected_df = pd.read_excel(groundtruth_file)
        
        # 检查基本结构
        required_columns = ['Time', 'Appliance types', 'Current Period Sales(Ten Thousand Units)', 'Accumulated Sales (Ten Thousand Units)', 'Year-on-Year Growth (%)', 'Accumulated Growth (%)']
        
        # 检查列名是否正确
        missing_columns = []
        for col in required_columns:
            if col not in agent_df.columns:
                missing_columns.append(col)
        
        if missing_columns:
            return False, f"Missing required columns: {missing_columns}"
        
        # 检查数据行数是否合理（应该有大量记录，因为是从二维转为一维）
        if len(agent_df) < 150: 
            print(f"Warning: Expected more records for flattened data, but found {len(agent_df)}")
        
        # 与参考答案比较基本统计信息
        expected_row_count = len(expected_df)
        if abs(len(agent_df) - expected_row_count) > 5:  # 允许一定的误差
            print(f"Warning: Row count mismatch. Expected ~{expected_row_count}, got {len(agent_df)}")
        
        # 检查是否包含预期的家电种类
        expected_appliances = ['Household Refrigerator', 'Air Conditioner', 'Household Washing Machines']
        agent_appliances = agent_df['Appliance types'].unique().tolist()
        
        found_appliances = []
        for appliance in expected_appliances:
            if appliance in agent_appliances:
                found_appliances.append(appliance)
        
        if len(found_appliances) < 3:
            missing_appliances = [app for app in expected_appliances if app not in found_appliances]
            return False, f"Missing appliance types: {missing_appliances}"
        
        # 检查数据值是否为数值类型（非字符串）
        numeric_columns = ['Current Period Sales(Ten Thousand Units)', 'Accumulated Sales (Ten Thousand Units)']
        for col in numeric_columns:
            if col in agent_df.columns:
                # 检查是否有有效的数值数据
                numeric_count = pd.to_numeric(agent_df[col], errors='coerce').notna().sum()
                if numeric_count == 0:
                    return False, f"No valid numeric data found in column '{col}'"
        
        # 检查时间列格式
        if 'Time' in agent_df.columns:
            time_count = agent_df['Time'].notna().sum()
            if time_count == 0:
                return False, "No valid time data found"
        
        # 简单的数据完整性检查
        if len(agent_df) > 0:
            # 检查每个时间点是否都有三种家电的数据
            if 'Time' in agent_df.columns and 'Appliance types' in agent_df.columns:
                time_appliance_combinations = agent_df.groupby('Time')['Appliance types'].nunique()
                incomplete_times = time_appliance_combinations[time_appliance_combinations < 3].index.tolist()
                
                if len(incomplete_times) > len(agent_df) // 4:  # 如果超过1/4的时间点数据不完整，则失败
                    return False, f"Too many time periods don't have all 3 appliance types: {len(incomplete_times)} periods"
        
        return True, None
    
    except Exception as e:
        return False, f"Error evaluating Excel transformation: {e}"
