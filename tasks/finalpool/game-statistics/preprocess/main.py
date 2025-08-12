import asyncio
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path
import os
import json
import logging
from datetime import datetime, date, timedelta
from google.cloud import bigquery
from google.oauth2 import service_account
from google.api_core.exceptions import Conflict, GoogleAPICallError, NotFound
import random
import numpy as np

# Enable verbose logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_player_skill_level():
    """生成玩家技能等级，模拟真实的技能分布"""
    # 使用正态分布生成技能等级，大部分玩家在中等水平
    skill = np.random.normal(50, 15)  # 平均50，标准差15
    return max(10, min(90, skill))  # 限制在10-90之间

def generate_realistic_score(base_skill, game_difficulty=1.0, variability=0.3):
    """基于技能等级生成更真实的得分"""
    # 基础得分基于技能
    base_score = base_skill * 10 + random.randint(-50, 50)
    
    # 游戏难度影响
    difficulty_modifier = random.uniform(0.8, 1.2) * game_difficulty
    
    # 随机波动（模拟运气、状态等因素）
    random_factor = random.uniform(1 - variability, 1 + variability)
    
    final_score = int(base_score * difficulty_modifier * random_factor)
    return max(0, final_score)

def get_realistic_region_distribution():
    """返回更真实的地区分布权重"""
    regions = ["US", "EU", "ASIA", "CN"]
    weights = [0.3, 0.25, 0.25, 0.2]  # 美国稍多，其他相对均匀
    return random.choices(regions, weights=weights)[0]

def generate_game_timestamps(base_time, game_count):
    """为一个玩家的多场游戏生成不同的时间戳"""
    timestamps = []
    current_time = base_time
    
    for i in range(game_count):
        # 每场游戏间隔随机时间（1-60分钟）
        if i > 0:
            interval_minutes = random.randint(1, 60)
            current_time += timedelta(minutes=interval_minutes)
        timestamps.append(current_time)
    
    return timestamps

def generate_historical_stats_data(days_back=10, players_per_day=100):
    """生成历史统计数据（前N天的前100名玩家数据）"""
    historical_data = []
    today = date.today()
    
    print(f"📊 生成历史统计数据：过去 {days_back} 天，每天 {players_per_day} 名玩家")
    
    for day_offset in range(1, days_back + 1):
        target_date = today - timedelta(days=day_offset)
        print(f"   生成 {target_date} 的数据...")
        
        # 为这一天生成玩家数据
        day_players = []
        for rank in range(1, players_per_day + 1):
            # 生成玩家技能等级（排名越靠前技能越高）
            base_skill = 95 - (rank - 1) * 0.5 + random.uniform(-5, 5)
            base_skill = max(20, min(95, base_skill))
            
            # 生成该玩家当天的总得分
            online_score = generate_realistic_score(base_skill, 1.0, 0.2) * random.randint(3, 8)
            task_score = generate_realistic_score(base_skill, 1.2, 0.25) * random.randint(2, 6)
            total_score = online_score + task_score
            
            # 游戏场数
            game_count = random.randint(3, 12)
            
            day_players.append({
                "player_id": f"player_{rank:03d}_{target_date.strftime('%m%d')}",
                "player_region": get_realistic_region_distribution(),
                "date": target_date.isoformat(),
                "total_online_score": online_score,
                "total_task_score": task_score,
                "total_score": total_score,
                "game_count": game_count
            })
        
        # 根据总分排序（确保排名正确）
        day_players.sort(key=lambda x: x["total_score"], reverse=True)
        historical_data.extend(day_players)
    
    print(f"✅ 生成了 {len(historical_data)} 条历史统计记录")
    return historical_data

def cleanup_existing_dataset(client: bigquery.Client, project_id: str):
    """
    Clean up existing game_analytics dataset if it exists
    """
    dataset_id = f"{project_id}.game_analytics"
    print(f"🧹 检查并清理现有数据集: {dataset_id}")
    
    try:
        # First try to get dataset info to see if it exists
        try:
            dataset = client.get_dataset(dataset_id)
            print(f"ℹ️  找到现有数据集: {dataset_id}")
            
            # List all tables in the dataset
            tables = list(client.list_tables(dataset_id))
            if tables:
                print(f"ℹ️  数据集包含 {len(tables)} 个表:")
                for table in tables:
                    print(f"   - {table.table_id}")
        except NotFound:
            print(f"ℹ️  数据集 {dataset_id} 不存在，无需清理")
            return
        
        # Delete dataset with all contents
        print(f"🗑️  删除数据集及其所有内容...")
        client.delete_dataset(
            dataset_id, 
            delete_contents=True, 
            not_found_ok=True
        )
        print(f"✅ 已成功清理数据集 '{dataset_id}' 及其所有内容")
        
        # Wait a moment for deletion to propagate
        import time
        time.sleep(2)
        
    except NotFound:
        print(f"ℹ️  数据集 {dataset_id} 不存在，无需清理")
    except Exception as e:
        print(f"❌ 数据集清理过程出错: {e}")
        logger.exception("Dataset cleanup failed")
        raise

def setup_bigquery_resources(credentials_path: str, project_id: str):
    """
    Setup BigQuery dataset and tables, then populate with sample data
    """
    print("=" * 60)
    print("🎯 开始设置 BigQuery 游戏统计资源")
    print("=" * 60)
    
    try:
        print(f"🔗 正在使用凭证 '{credentials_path}' 连接到项目 '{project_id}'...")
        
        # Use the newer authentication method
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(credentials=credentials, project=project_id)
        
        print("✅ 连接成功！")
        
        # Test connection by listing datasets
        print("🔍 测试连接 - 列出现有数据集...")
        try:
            datasets = list(client.list_datasets())
            print(f"ℹ️  项目中现有 {len(datasets)} 个数据集")
            for dataset in datasets:
                print(f"   - {dataset.dataset_id}")
        except Exception as e:
            print(f"⚠️  列出数据集时出错: {e}")

        # Clean up existing dataset first
        cleanup_existing_dataset(client, project_id)

        # Create dataset
        dataset_id = f"{project_id}.game_analytics"
        print(f"📊 创建数据集: {dataset_id}")
        try:
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"
            dataset.description = "Game analytics dataset for daily scoring and leaderboards"
            client.create_dataset(dataset, timeout=30)
            print(f"✅ 数据集 '{dataset.dataset_id}' 已成功创建。")
        except Conflict:
            print(f"ℹ️  数据集 '{dataset_id}' 已存在，跳过创建。")
        except Exception as e:
            print(f"❌ 创建数据集失败: {e}")
            logger.exception("Dataset creation failed")
            raise

        # Create daily_scores_stream table
        table_id_stream = f"{dataset_id}.daily_scores_stream"
        print(f"🗂️  创建表: {table_id_stream}")
        schema_stream = [
            bigquery.SchemaField("player_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("player_region", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("scores", "RECORD", mode="NULLABLE", fields=[
                bigquery.SchemaField("online_score", "INTEGER"),
                bigquery.SchemaField("task_score", "INTEGER"),
            ]),
            bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        ]
        table_stream = bigquery.Table(table_id_stream, schema=schema_stream)
        table_stream.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="timestamp",
        )
        try:
            client.create_table(table_stream)
            print(f"✅ 表 '{table_id_stream}' 已成功创建。")
        except Conflict:
            print(f"ℹ️  表 '{table_id_stream}' 已存在，跳过创建。")
        except Exception as e:
            print(f"❌ 创建表 '{table_id_stream}' 失败: {e}")
            raise

        # Create player_historical_stats table
        table_id_stats = f"{dataset_id}.player_historical_stats"
        print(f"🗂️  创建表: {table_id_stats}")
        schema_stats = [
            bigquery.SchemaField("player_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("player_region", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("total_online_score", "INTEGER"),
            bigquery.SchemaField("total_task_score", "INTEGER"),
            bigquery.SchemaField("total_score", "INTEGER", description="当日总分 (online + task)"),
            bigquery.SchemaField("game_count", "INTEGER"),
        ]
        table_stats = bigquery.Table(table_id_stats, schema=schema_stats)
        try:
            client.create_table(table_stats)
            print(f"✅ 表 '{table_id_stats}' 已成功创建。")
        except Conflict:
            print(f"ℹ️  表 '{table_id_stats}' 已存在，跳过创建。")
        except Exception as e:
            print(f"❌ 创建表 '{table_id_stats}' 失败: {e}")
            raise

        # Populate with sample data for current date
        today = date.today()
        current_time = datetime.now()
        print(f"📈 开始生成样本数据，当前日期: {today}")
        
        # Generate improved sample data for daily_scores_stream
        sample_rows = []
        player_count = 200
        print(f"👥 为 {player_count} 个玩家生成改进的游戏数据...")
        
        # 为每个玩家预先生成技能等级
        player_skills = {}
        for player_id in range(1, player_count + 1):
            player_skills[player_id] = generate_player_skill_level()
        
        for player_id in range(1, player_count + 1):
            # 更真实的游戏场次分布
            games_count = random.choices([3, 4, 5, 6, 7, 8, 9, 10], 
                                       weights=[5, 10, 15, 20, 20, 15, 10, 5])[0]
            
            # 为该玩家生成游戏时间戳
            start_time = current_time - timedelta(hours=random.randint(0, 12))
            timestamps = generate_game_timestamps(start_time, games_count)
            
            player_skill = player_skills[player_id]
            player_region = get_realistic_region_distribution()
            
            for game_num in range(games_count):
                # 使用改进的得分生成函数
                game_difficulty = random.uniform(0.8, 1.5)  # 随机游戏难度
                online_score = generate_realistic_score(player_skill, game_difficulty, 0.3)
                task_score = generate_realistic_score(player_skill, game_difficulty * 1.2, 0.4)
                
                sample_rows.append({
                    "player_id": f"player_{player_id:03d}",
                    "player_region": player_region,
                    "scores": {
                        "online_score": online_score,
                        "task_score": task_score,
                    },
                    "game_id": f"game_{player_id:03d}_{game_num:02d}_{today.strftime('%Y%m%d')}",
                    "timestamp": timestamps[game_num].isoformat()
                })
        
        print(f"📝 生成了 {len(sample_rows)} 条改进的样本记录")

        # Insert sample data with detailed error handling
        print(f"💾 插入样本数据到 daily_scores_stream...")
        try:
            table_ref = client.get_table(table_id_stream)
            print(f"✅ 获取到表引用: {table_ref.table_id}")
            
            # Insert in smaller batches to avoid timeouts
            batch_size = 100
            total_inserted = 0
            for i in range(0, len(sample_rows), batch_size):
                batch = sample_rows[i:i + batch_size]
                print(f"   插入批次 {i//batch_size + 1}: {len(batch)} 条记录...")
                
                errors = client.insert_rows_json(table_ref, batch)
                if errors:
                    print(f"❌ 批次 {i//batch_size + 1} 插入错误: {errors}")
                    for error in errors:
                        logger.error(f"Insert error: {error}")
                    raise Exception(f"批次插入失败: {errors}")
                else:
                    total_inserted += len(batch)
                    print(f"   ✅ 批次 {i//batch_size + 1} 成功插入 {len(batch)} 条记录")
            
            print(f"🎉 成功插入总计 {total_inserted} 条样本数据到 daily_scores_stream 表")
            
            # Verify data insertion
            print("🔍 验证数据插入...")
            query = f"""
            SELECT COUNT(*) as total_rows, 
                   COUNT(DISTINCT player_id) as unique_players,
                   DATE(timestamp) as data_date
            FROM `{table_id_stream}`
            WHERE DATE(timestamp) = '{today}'
            GROUP BY DATE(timestamp)
            """
            query_job = client.query(query)
            results = list(query_job.result())
            if results:
                result = results[0]
                print(f"✅ 验证成功: {result.total_rows} 行数据, {result.unique_players} 个独特玩家, 日期: {result.data_date}")
            else:
                print("⚠️  验证查询未返回结果")
                
        except Exception as e:
            print(f"❌ 插入数据时出现错误: {e}")
            logger.exception("Data insertion failed")
            raise Exception(f"插入数据失败: {e}")

        # Generate and insert historical data for player_historical_stats
        print(f"\n📈 开始生成并插入历史统计数据...")
        try:
            historical_data = generate_historical_stats_data(days_back=10, players_per_day=100)
            
            # Insert historical data
            table_ref_stats = client.get_table(table_id_stats)
            print(f"💾 插入历史统计数据到 player_historical_stats...")
            
            # Insert in batches
            batch_size = 100
            total_inserted = 0
            for i in range(0, len(historical_data), batch_size):
                batch = historical_data[i:i + batch_size]
                print(f"   插入历史数据批次 {i//batch_size + 1}: {len(batch)} 条记录...")
                
                errors = client.insert_rows_json(table_ref_stats, batch)
                if errors:
                    print(f"❌ 历史数据批次 {i//batch_size + 1} 插入错误: {errors}")
                    for error in errors:
                        logger.error(f"Historical data insert error: {error}")
                    raise Exception(f"历史数据批次插入失败: {errors}")
                else:
                    total_inserted += len(batch)
                    print(f"   ✅ 历史数据批次 {i//batch_size + 1} 成功插入 {len(batch)} 条记录")
            
            print(f"🎉 成功插入总计 {total_inserted} 条历史统计数据到 player_historical_stats 表")
            
            # Verify historical data insertion
            print("🔍 验证历史数据插入...")
            query = f"""
            SELECT COUNT(*) as total_rows, 
                   COUNT(DISTINCT date) as unique_dates,
                   MIN(date) as earliest_date,
                   MAX(date) as latest_date
            FROM `{table_id_stats}`
            """
            query_job = client.query(query)
            results = list(query_job.result())
            if results:
                result = results[0]
                print(f"✅ 历史数据验证成功: {result.total_rows} 行数据, {result.unique_dates} 个不同日期")
                print(f"   日期范围: {result.earliest_date} 到 {result.latest_date}")
            else:
                print("⚠️  历史数据验证查询未返回结果")
                
        except Exception as e:
            print(f"❌ 插入历史数据时出现错误: {e}")
            logger.exception("Historical data insertion failed")
            raise Exception(f"插入历史数据失败: {e}")

        return client, dataset_id

    except GoogleAPICallError as e:
        print(f"❌ Google Cloud API 调用失败: {e}")
        logger.exception("Google Cloud API call failed")
        raise
    except Exception as e:
        print(f"❌ 设置过程中发生错误: {e}")
        logger.exception("Setup process failed")
        raise

def get_project_id_from_key(credentials_path: str) -> str | None:
    """从服务账号密钥文件中读取项目ID"""
    try:
        with open(credentials_path, 'r') as f:
            data = json.load(f)
            return data.get("project_id")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--credentials_file", default="configs/mcp-bench0606-2b68b5487343.json")
    parser.add_argument("--launch_time", nargs='*', required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()

    print("🎮 开始设置 BigQuery 游戏统计资源...")
    print("=" * 60)
    
    # Get credentials file path
    credentials_path = Path(args.credentials_file)
    
    # Make sure the path is absolute
    if not credentials_path.is_absolute():
        credentials_path = Path.cwd() / credentials_path
    
    if not credentials_path.exists():
        print(f"❌ 错误：凭证文件不存在: {credentials_path}")
        print("请确保服务账号密钥文件存在于指定路径")
        exit(1)
    else:
        print(f"✅ 找到凭证文件: {credentials_path}")
    
    project_id = get_project_id_from_key(str(credentials_path))
    
    if project_id:
        print(f"🆔 从凭证文件中成功读取项目ID: {project_id}")
        try:
            client, dataset_id = setup_bigquery_resources(str(credentials_path), project_id)
            print("\n" + "=" * 60)
            print("🎉 所有 BigQuery 资源设置完毕！")
            print("📊 已为当日生成样本游戏数据")
            print("🎯 任务：代理需要生成排行榜并更新历史统计数据")
            print("=" * 60)
        except Exception as e:
            print(f"\n❌ 设置失败: {e}")
            exit(1)
    else:
        print(f"❌ 无法从凭证文件中读取项目ID。")
        exit(1)