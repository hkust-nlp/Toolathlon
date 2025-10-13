#!/usr/bin/env python3
"""
Enhanced Game Statistics Evaluation Test Script

Tests the enhanced evaluation logic to verify:
1. The completeness of the daily leaderboard (including consistency with raw data)
2. The accuracy of historical statistics
3. Handling of error scenarios

Usage:
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
    """Test data manager."""
    
    def __init__(self, server):
        self.server = server
        self.today_str = date.today().strftime('%Y-%m-%d')
        self.table_name = f"leaderboard_{self.today_str.replace('-', '')}"
    
    async def create_correct_leaderboard(self):
        """Create correct leaderboard data (based on actual top 100)."""
        print("🔧 Creating correct leaderboard test data...")
        
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
            raise Exception("Cannot parse the daily scores query result")
        
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
        
        print(f"✅ Correct leaderboard {self.table_name} with {len(top100_players)} records created")
        return len(top100_players)
    
    async def create_incorrect_leaderboard_wrong_players(self):
        """Create incorrect leaderboard data (wrong players included)."""
        print("🔧 Creating incorrect leaderboard test data (wrong players)...")
        
        # Get actual top 110 players
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
        
        print(f"✅ Incorrect leaderboard (wrong players) created")
        return len(wrong_leaderboard)
    
    async def create_incorrect_leaderboard_wrong_scores(self):
        """Create incorrect leaderboard data (wrong scores)."""
        print("🔧 Creating incorrect leaderboard test data (wrong scores)...")
        
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
        
        print(f"✅ Incorrect leaderboard (wrong scores) created")
        return len(top100_players)
    
    async def create_correct_historical_stats(self):
        """Create correct historical statistics data."""
        print("🔧 Creating correct historical statistics test data...")
        
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
        
        print(f"✅ Correct historical statistics with {len(daily_stats)} records created")
        return len(daily_stats)
    
    async def cleanup_test_data(self):
        """Clean up test data."""
        print("🧹 Cleaning up test data...")
        
        try:
            # Drop leaderboard table
            await call_tool_with_retry(self.server, "bigquery_run_query", {
                "query": f"DROP TABLE IF EXISTS `game_analytics.{self.table_name}`"
            })
            print(f"✅ Leaderboard table {self.table_name} deleted")
        except Exception as e:
            print(f"⚠️  Error when deleting leaderboard table: {e}")

async def test_correct_leaderboard_validation(server):
    """Test correct leaderboard validation."""
    print("\n" + "="*60)
    print("🧪 Test 1: Correct leaderboard validation")
    print("="*60)
    
    test_manager = TestDataManager(server)
    today_str = test_manager.today_str
    
    try:
        # Create correct test data
        await test_manager.create_correct_leaderboard()
        
        # Run validation - should pass
        result = await verify_daily_leaderboard(server, today_str)
        
        print(f"\n📊 Test Result: {'✅ PASSED' if result else '❌ FAILED'}")
        
        if result:
            print("🎉 Correct leaderboard validation passed!")
        else:
            print("❌ Correct leaderboard validation failed, this should not happen.")
        
        return result
        
    finally:
        await test_manager.cleanup_test_data()

async def test_incorrect_leaderboard_players(server):
    """Test incorrect player leaderboard validation."""
    print("\n" + "="*60)
    print("🧪 Test 2: Incorrect player leaderboard validation")
    print("="*60)
    
    test_manager = TestDataManager(server)
    today_str = test_manager.today_str
    
    try:
        # Create incorrect test data (wrong players)
        await test_manager.create_incorrect_leaderboard_wrong_players()
        
        # Run validation - should fail
        result = await verify_daily_leaderboard(server, today_str)
        
        print(f"\n📊 Test Result: {'❌ DID NOT DETECT ERROR' if result else '✅ Correctly detected error'}")
        
        if not result:
            print("🎉 Error player detection succeeded!")
        else:
            print("❌ Should have detected error but did not.")
        
        return not result  # Test passes if validation fails
        
    finally:
        await test_manager.cleanup_test_data()

async def test_incorrect_leaderboard_scores(server):
    """Test incorrect score leaderboard validation."""
    print("\n" + "="*60)
    print("🧪 Test 3: Incorrect score leaderboard validation")
    print("="*60)
    
    test_manager = TestDataManager(server)
    today_str = test_manager.today_str
    
    try:
        # Create incorrect test data (wrong scores)
        await test_manager.create_incorrect_leaderboard_wrong_scores()
        
        # Run validation - should fail
        result = await verify_daily_leaderboard(server, today_str)
        
        print(f"\n📊 Test Result: {'❌ DID NOT DETECT ERROR' if result else '✅ Correctly detected error'}")
        
        if not result:
            print("🎉 Error score detection succeeded!")
        else:
            print("❌ Should have detected score error but did not.")
        
        return not result  # Test passes if validation fails
        
    finally:
        await test_manager.cleanup_test_data()

async def test_historical_stats_validation(server):
    """Test historical statistics validation."""
    print("\n" + "="*60)
    print("🧪 Test 4: Historical statistics validation")
    print("="*60)
    
    test_manager = TestDataManager(server)
    today_str = test_manager.today_str
    
    try:
        # Create correct historical stats
        await test_manager.create_correct_historical_stats()
        
        # Run validation - should pass
        result = await verify_historical_stats_update(server, today_str)
        
        print(f"\n📊 Test Result: {'✅ PASSED' if result else '❌ FAILED'}")
        
        if result:
            print("🎉 Historical stats validation passed!")
        else:
            print("❌ Historical stats validation failed.")
        
        return result
        
    except Exception as e:
        print(f"❌ Error occurred during test: {e}")
        return False

async def run_enhanced_evaluation_tests(test_failures=False):
    """Run enhanced evaluation tests."""
    print("🎯 Starting enhanced game statistics evaluation tests...")
    print(f"📅 Test Date: {date.today().strftime('%Y-%m-%d')}")
    
    xx_MCPServerManager = MCPServerManager(agent_workspace="./")
    google_cloud_server = xx_MCPServerManager.servers['google-cloud']
    
    test_results = []
    
    async with google_cloud_server as server:
        # Test 1: Correct leaderboard validation
        result1 = await test_correct_leaderboard_validation(server)
        test_results.append(("Correct Leaderboard Validation", result1))
        
        if test_failures:
            # Test 2: Incorrect players detection
            result2 = await test_incorrect_leaderboard_players(server)
            test_results.append(("Wrong Player Detection", result2))
            
            # Test 3: Incorrect scores detection
            result3 = await test_incorrect_leaderboard_scores(server)
            test_results.append(("Wrong Score Detection", result3))
        
        # Test 4: Historical stats validation
        result4 = await test_historical_stats_validation(server)
        test_results.append(("Historical Stats Validation", result4))
    
    # Print summary
    print("\n" + "="*60)
    print("📈 Test Summary")
    print("="*60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced evaluation logic is working correctly.")
        return 0
    else:
        print("❌ Some tests failed, please check the enhanced evaluation logic.")
        return 1

async def main():
    parser = ArgumentParser(description="Enhanced Game Statistics Evaluation Test")
    parser.add_argument("--test_failures", action="store_true", 
                       help="Whether to test error detection capability (including error scenarios)")
    args = parser.parse_args()
    
    try:
        exit_code = await run_enhanced_evaluation_tests(test_failures=args.test_failures)
        return exit_code
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    print(f"\n🏁 Testing completed, exit code: {exit_code}")
    sys.exit(exit_code)