#!/usr/bin/env python3
"""
便捷的任务设置脚本
用于快速设置测试环境和运行评估
"""

import os
import sys
import argparse
from pathlib import Path

# 添加项目路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / 'preprocess'))
sys.path.insert(0, str(current_dir / 'evaluation'))

def setup_test_products():
    """设置测试商品"""
    print("🚀 开始设置测试商品...")
    
    try:
        from preprocess.setup_test_products import main as setup_main
        success = setup_main()
        if success:
            print("✅ 测试商品设置完成！")
            return True
        else:
            print("❌ 测试商品设置失败！")
            return False
    except Exception as e:
        print(f"❌ 设置过程中出错: {e}")
        return False

def clear_store():
    """清理商店"""
    print("🧹 开始清理商店...")
    
    try:
        from preprocess.setup_test_products import clear_store_only
        success = clear_store_only()
        if success:
            print("✅ 商店清理完成！")
            return True
        else:
            print("⚠️ 商店清理部分完成")
            return False
    except Exception as e:
        print(f"❌ 清理过程中出错: {e}")
        return False

# def run_evaluation(agent_workspace=None, groundtruth_workspace=None, res_log_file=None):
#     """运行评估"""
#     print("📊 开始运行评估...")
    
#     try:
#         from evaluation.main import main as eval_main
#         import subprocess
#         import sys
        
#         # 使用默认路径如果未提供
#         if not agent_workspace:
#             agent_workspace = str(current_dir / 'workspace')
#         if not groundtruth_workspace:
#             groundtruth_workspace = str(current_dir / 'groundtruth_workspace')
        
#         # 构建评估命令
#         eval_script = current_dir / 'evaluation' / 'main.py'
#         cmd = [sys.executable, str(eval_script)]
#         cmd.extend(['--agent_workspace', agent_workspace])
#         cmd.extend(['--groundtruth_workspace', groundtruth_workspace])
        
#         if res_log_file and os.path.exists(res_log_file):
#             cmd.extend(['--res_log_file', res_log_file])
        
#         # 运行评估
#         result = subprocess.run(cmd, capture_output=True, text=True)
        
#         if result.returncode == 0:
#             print("✅ 评估通过")
#             print(result.stdout)
#             return True
#         else:
#             print("❌ 评估失败")
#             print(result.stderr)
#             return False
            
#     except Exception as e:
#         print(f"❌ 评估过程中出错: {e}")
#         return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='低销量产品筛选任务设置和评估工具')
    parser.add_argument('--setup', action='store_true', help='设置测试商品')
    parser.add_argument('--clear', action='store_true', help='清理商店')
    parser.add_argument('--eval', action='store_true', help='运行评估')
    parser.add_argument('--full', action='store_true', help='完整流程：清理+设置+评估')
    parser.add_argument('--agent-workspace', help='Agent工作空间路径')
    parser.add_argument('--groundtruth-workspace', help='Ground truth工作空间路径')
    
    args = parser.parse_args()
    
    if not any([args.setup, args.clear, args.eval, args.full]):
        parser.print_help()
        return
    
    print("=" * 60)
    print("🎯 低销量产品筛选任务设置和评估工具")
    print("=" * 60)
    
    success = True
    
    if args.full or args.clear:
        success &= clear_store()
    
    if args.full or args.setup:
        success &= setup_test_products()
    
    if args.full or args.eval:
        success &= run_evaluation(args.agent_workspace, args.groundtruth_workspace)
    
    if success:
        print("\n🎉 所有操作完成！")
    else:
        print("\n⚠️ 部分操作失败，请查看上方日志")

if __name__ == '__main__':
    main()