#!/usr/bin/env python3
"""
增强版游戏统计任务评估测试脚本

测试增强后的evaluation逻辑，验证：
1. 每日排行榜的完整性验证（包括与原始数据的一致性检查）
2. 历史统计数据的准确性验证
3. 错误场景的处理能力

使用方法:
python test_enhanced_evaluation.py [--create_test_data] [--test_failures]
"""

import asyncio
import json
import sys
from argparse import ArgumentParser
from datetime import datetime, date, timedelta
from pathlib import Path
from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError

# Add current directory to path to import evaluation functions
import sys
sys.path.append(str(Path(__file__).parent))
from evaluation.main import verify_daily_leaderboard, verify_historical_stats_update

class TestDataManager:
    """测试数据管理器"""
    
    def __init__(self, server):
        self.server = server
        self.today_str = date.today().strftime('%Y-%m-%d')
        self.table_name = f"leaderboard_{self.today_str.replace('-', '')}"
    
    async def create_correct_leaderboard(self):
        """创建正确的排行榜数据（基于真实的top100）"""
        print("🔧 创建正确的排行榜测试数据...")
        
        # First get the actual top 100 players from daily_scores_stream
        daily_query_result = await call_tool_with_retry(self.server, "bigquery_run_query", {
            "query": f"""
            SELECT 
                player_id,
                SUM(scores.online_score + scores.task_score) as total_score
            FROM `game_analytics.daily_scores_stream`
            WHERE DATE(timestamp) = '{self.today_str}'
            GROUP BY player_id
            ORDER BY total_score DESC
            LIMIT 100
            """
        })
        
        content = daily_query_result.content[0].text
        start_pos = content.find("[")
        end_pos = content.rfind("]")
        if start_pos == -1 or end_pos == -1:
            raise Exception("无法解析每日分数查询结果")
        
        top100_players = json.loads(content[start_pos:end_pos+1])
        
        # Create leaderboard table
        await call_tool_with_retry(self.server, "bigquery_run_query", {
            "query": f"""
            CREATE OR REPLACE TABLE `game_analytics.{self.table_name}` (
                player_id STRING,
                total_score INTEGER,
                rank INTEGER
            )
            """
        })
        
        # Insert correct leaderboard data
        insert_values = []
        for i, player in enumerate(top100_players, 1):
            insert_values.append(f"('{player['player_id']}', {player['total_score']}, {i})")
        
        values_str = ",\n    ".join(insert_values)
        await call_tool_with_retry(self.server, "bigquery_run_query", {
            "query": f"""
            INSERT INTO `game_analytics.{self.table_name}` (player_id, total_score, rank)
            VALUES
                {values_str}
            """
        })
        
        print(f"✅ 已创建正确的排行榜 {self.table_name} 包含 {len(top100_players)} 条记录")
        return len(top100_players)
    
    async def create_incorrect_leaderboard_wrong_players(self):
        """创建错误的排行榜数据（包含错误的玩家）"""
        print("🔧 创建错误排行榜测试数据（错误玩家）...")
        
        # Get actual top 100 players
        daily_query_result = await call_tool_with_retry(self.server, "bigquery_run_query", {
            "query": f"""
            SELECT 
                player_id,
                SUM(scores.online_score + scores.task_score) as total_score
            FROM `game_analytics.daily_scores_stream`
            WHERE DATE(timestamp) = '{self.today_str}'
            GROUP BY player_id
            ORDER BY total_score DESC
            LIMIT 110
            """
        })
        
        content = daily_query_result.content[0].text
        start_pos = content.find("[")
        end_pos = content.rfind("]")
        top110_players = json.loads(content[start_pos:end_pos+1])
        
        # Create wrong leaderboard: take top 90 + bottom 10 (should be 101-110)
        wrong_leaderboard = top110_players[:90] + top110_players[100:110]
        
        # Create table and insert wrong data
        await call_tool_with_retry(self.server, "bigquery_run_query", {
            "query": f"""
            CREATE OR REPLACE TABLE `game_analytics.{self.table_name}` (
                player_id STRING,
                total_score INTEGER,
                rank INTEGER
            )
            """
        })
        
        insert_values = []
        for i, player in enumerate(wrong_leaderboard, 1):
            insert_values.append(f"('{player['player_id']}', {player['total_score']}, {i})")
        
        values_str = ",\n    ".join(insert_values)
        await call_tool_with_retry(self.server, "bigquery_run_query", {
            "query": f"""
            INSERT INTO `game_analytics.{self.table_name}` (player_id, total_score, rank)
            VALUES
                {values_str}
            """
        })
        
        print(f"✅ 已创建错误排行榜（错误玩家）")
        return len(wrong_leaderboard)
    
    async def create_incorrect_leaderboard_wrong_scores(self):
        """创建错误的排行榜数据（分数错误）"""
        print("🔧 创建错误排行榜测试数据（分数错误）...")
        
        # Get actual top 100 players
        daily_query_result = await call_tool_with_retry(self.server, "bigquery_run_query", {
            "query": f"""
            SELECT 
                player_id,
                SUM(scores.online_score + scores.task_score) as total_score
            FROM `game_analytics.daily_scores_stream`
            WHERE DATE(timestamp) = '{self.today_str}'
            GROUP BY player_id
            ORDER BY total_score DESC
            LIMIT 100
            """
        })
        
        content = daily_query_result.content[0].text
        start_pos = content.find("[")
        end_pos = content.rfind("]")
        top100_players = json.loads(content[start_pos:end_pos+1])
        
        # Create table
        await call_tool_with_retry(self.server, "bigquery_run_query", {
            "query": f"""
            CREATE OR REPLACE TABLE `game_analytics.{self.table_name}` (
                player_id STRING,
                total_score INTEGER,
                rank INTEGER
            )
            """
        })
        
        # Insert with wrong scores (add 100 to first 10 players' scores)
        insert_values = []
        for i, player in enumerate(top100_players, 1):
            wrong_score = player['total_score'] + (100 if i <= 10 else 0)
            insert_values.append(f"('{player['player_id']}', {wrong_score}, {i})")
        
        values_str = ",\n    ".join(insert_values)
        await call_tool_with_retry(self.server, "bigquery_run_query", {
            "query": f"""
            INSERT INTO `game_analytics.{self.table_name}` (player_id, total_score, rank)
            VALUES
                {values_str}
            """
        })
        
        print(f"✅ 已创建错误排行榜（分数错误）")
        return len(top100_players)
    
    async def create_correct_historical_stats(self):
        """创建正确的历史统计数据"""
        print("🔧 创建正确的历史统计测试数据...")
        
        # Get aggregated data from daily_scores_stream
        daily_query_result = await call_tool_with_retry(self.server, "bigquery_run_query", {
            "query": f"""
            SELECT 
                player_id,
                SUM(scores.online_score + scores.task_score) as total_score,
                COUNT(*) as game_count
            FROM `game_analytics.daily_scores_stream`
            WHERE DATE(timestamp) = '{self.today_str}'
            GROUP BY player_id
            """
        })
        
        content = daily_query_result.content[0].text
        start_pos = content.find("[")
        end_pos = content.rfind("]")
        daily_stats = json.loads(content[start_pos:end_pos+1])
        
        # Clear existing today's records and insert correct ones
        await call_tool_with_retry(self.server, "bigquery_run_query", {
            "query": f"""
            DELETE FROM `game_analytics.player_historical_stats`
            WHERE date = '{self.today_str}'
            """
        })
        
        # Insert correct historical stats
        insert_values = []
        for player in daily_stats:
            insert_values.append(
                f"('{player['player_id']}', 'US', '{self.today_str}', "
                f"0, {player['total_score']}, {player['total_score']}, {player['game_count']})"
            )
        
        if insert_values:
            values_str = ",\n    ".join(insert_values)
            await call_tool_with_retry(self.server, "bigquery_run_query", {
                "query": f"""
                INSERT INTO `game_analytics.player_historical_stats` 
                (player_id, player_region, date, total_online_score, total_task_score, total_score, game_count)
                VALUES
                    {values_str}
                """
            })
        
        print(f"✅ 已创建正确的历史统计数据 {len(daily_stats)} 条记录")
        return len(daily_stats)
    
    async def cleanup_test_data(self):
        """清理测试数据"""
        print("🧹 清理测试数据...")
        
        try:
            # Drop leaderboard table
            await call_tool_with_retry(self.server, "bigquery_run_query", {
                "query": f"DROP TABLE IF EXISTS `game_analytics.{self.table_name}`"
            })
            print(f"✅ 已删除排行榜表 {self.table_name}")
        except Exception as e:
            print(f"⚠️  删除排行榜表时出错: {e}")

async def test_correct_leaderboard_validation(server):
    """测试正确排行榜的验证"""
    print("\n" + "="*60)
    print("🧪 测试 1: 正确排行榜验证")
    print("="*60)
    
    test_manager = TestDataManager(server)
    today_str = test_manager.today_str
    
    try:
        # Create correct test data
        await test_manager.create_correct_leaderboard()
        
        # Run validation - should pass
        result = await verify_daily_leaderboard(server, today_str)
        
        print(f"\n📊 测试结果: {'✅ 通过' if result else '❌ 失败'}")
        
        if result:
            print("🎉 正确排行榜验证成功通过！")
        else:
            print("❌ 正确排行榜验证失败，这不应该发生")
        
        return result
        
    finally:
        await test_manager.cleanup_test_data()

async def test_incorrect_leaderboard_players(server):
    """测试错误玩家的排行榜验证"""
    print("\n" + "="*60)
    print("🧪 测试 2: 错误玩家排行榜验证")
    print("="*60)
    
    test_manager = TestDataManager(server)
    today_str = test_manager.today_str
    
    try:
        # Create incorrect test data (wrong players)
        await test_manager.create_incorrect_leaderboard_wrong_players()
        
        # Run validation - should fail
        result = await verify_daily_leaderboard(server, today_str)
        
        print(f"\n📊 测试结果: {'❌ 错误检测失败' if result else '✅ 正确检测到错误'}")
        
        if not result:
            print("🎉 错误玩家检测成功！")
        else:
            print("❌ 应该检测到错误但没有检测到")
        
        return not result  # Test passes if validation fails
        
    finally:
        await test_manager.cleanup_test_data()

async def test_incorrect_leaderboard_scores(server):
    """测试错误分数的排行榜验证"""
    print("\n" + "="*60)
    print("🧪 测试 3: 错误分数排行榜验证")
    print("="*60)
    
    test_manager = TestDataManager(server)
    today_str = test_manager.today_str
    
    try:
        # Create incorrect test data (wrong scores)
        await test_manager.create_incorrect_leaderboard_wrong_scores()
        
        # Run validation - should fail
        result = await verify_daily_leaderboard(server, today_str)
        
        print(f"\n📊 测试结果: {'❌ 错误检测失败' if result else '✅ 正确检测到错误'}")
        
        if not result:
            print("🎉 错误分数检测成功！")
        else:
            print("❌ 应该检测到分数错误但没有检测到")
        
        return not result  # Test passes if validation fails
        
    finally:
        await test_manager.cleanup_test_data()

async def test_historical_stats_validation(server):
    """测试历史统计验证"""
    print("\n" + "="*60)
    print("🧪 测试 4: 历史统计验证")
    print("="*60)
    
    test_manager = TestDataManager(server)
    today_str = test_manager.today_str
    
    try:
        # Create correct historical stats
        await test_manager.create_correct_historical_stats()
        
        # Run validation - should pass
        result = await verify_historical_stats_update(server, today_str)
        
        print(f"\n📊 测试结果: {'✅ 通过' if result else '❌ 失败'}")
        
        if result:
            print("🎉 历史统计验证成功通过！")
        else:
            print("❌ 历史统计验证失败")
        
        return result
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        return False

async def run_enhanced_evaluation_tests(test_failures=False):
    """运行增强版评估测试"""
    print("🎯 开始增强版游戏统计评估测试...")
    print(f"📅 测试日期: {date.today().strftime('%Y-%m-%d')}")
    
    xx_MCPServerManager = MCPServerManager(agent_workspace="./")
    google_cloud_server = xx_MCPServerManager.servers['google-cloud']
    
    test_results = []
    
    async with google_cloud_server as server:
        # Test 1: Correct leaderboard validation
        result1 = await test_correct_leaderboard_validation(server)
        test_results.append(("正确排行榜验证", result1))
        
        if test_failures:
            # Test 2: Incorrect players detection
            result2 = await test_incorrect_leaderboard_players(server)
            test_results.append(("错误玩家检测", result2))
            
            # Test 3: Incorrect scores detection
            result3 = await test_incorrect_leaderboard_scores(server)
            test_results.append(("错误分数检测", result3))
        
        # Test 4: Historical stats validation
        result4 = await test_historical_stats_validation(server)
        test_results.append(("历史统计验证", result4))
    
    # Print summary
    print("\n" + "="*60)
    print("📈 测试总结")
    print("="*60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总体结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！增强版评估逻辑工作正常。")
        return 0
    else:
        print("❌ 部分测试失败，请检查增强版评估逻辑。")
        return 1

async def main():
    parser = ArgumentParser(description="增强版游戏统计任务评估测试")
    parser.add_argument("--test_failures", action="store_true", 
                       help="是否测试错误检测能力（包括错误场景测试）")
    args = parser.parse_args()
    
    try:
        exit_code = await run_enhanced_evaluation_tests(test_failures=args.test_failures)
        return exit_code
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    print(f"\n🏁 测试完成，退出码: {exit_code}")
    sys.exit(exit_code)