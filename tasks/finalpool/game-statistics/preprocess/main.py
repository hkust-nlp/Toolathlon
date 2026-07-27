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
random.seed(42)

# Enable verbose logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Persist the resolved task date so evaluation can reuse preprocess' date
# when launch_time is unavailable.
TASK_DATE_FILENAME = "task_date.txt"
WORKSPACE_TASK_DATE_FILENAME = ".task_date.txt"


def parse_task_date(launch_time: str | None) -> date:
    """Resolve the task date from launch_time, falling back to the system date."""
    if not launch_time:
        return date.today()

    normalized = launch_time.strip()
    candidates = [normalized]
    parts = normalized.split()
    if len(parts) > 1:
        candidates.append(" ".join(parts[:-1]))

    for candidate in candidates:
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue

    raise ValueError(
        f"Could not parse launch_time '{launch_time}'. "
        "Supported formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, "
        "or YYYY-MM-DD HH:MM:SS <weekday>."
    )


def save_task_date(task_date: date, agent_workspace: str | None = None):
    """Save the resolved task date for evaluation fallback."""
    candidate_paths = [
        Path(__file__).resolve().parent.parent / "groundtruth_workspace" / TASK_DATE_FILENAME,
    ]
    if agent_workspace:
        candidate_paths.append(Path(agent_workspace) / WORKSPACE_TASK_DATE_FILENAME)

    saved_paths = []
    for path in candidate_paths:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(task_date.isoformat(), encoding="utf-8")
            saved_paths.append(path)
        except OSError as exc:
            print(f"⚠️  Failed to save task date to {path}: {exc}")

    if not saved_paths:
        raise OSError("Failed to persist task date for evaluation")

    print(f"📌 Task date anchored to {task_date.isoformat()}")
    for path in saved_paths:
        print(f"   Saved task date to: {path}")


def generate_safe_start_time(task_date: date, game_count: int) -> datetime:
    """Generate a start time that keeps all generated games on task_date."""
    latest_start_minute = max(0, 23 * 60 + 59 - 60 * (game_count - 1))
    start_total_minute = random.randint(0, latest_start_minute)
    return datetime.combine(task_date, datetime.min.time()) + timedelta(minutes=start_total_minute)

def generate_player_skill_level():
    """Generate player's skill level, simulating a realistic skill distribution."""
    # Use normal distribution centered at 50 with a standard deviation of 15
    skill = np.random.normal(50, 15)
    return max(10, min(90, skill))  # Clamp skill between 10 and 90

def generate_realistic_score(base_skill, game_difficulty=1.0, variability=0.3):
    """Generate a realistic score based on skill level."""
    base_score = base_skill * 10 + random.randint(-50, 50)
    difficulty_modifier = random.uniform(0.8, 1.2) * game_difficulty
    random_factor = random.uniform(1 - variability, 1 + variability)
    final_score = int(base_score * difficulty_modifier * random_factor)
    return max(0, final_score)

def get_realistic_region_distribution():
    """Return a region weighted more realistically."""
    regions = ["US", "EU", "ASIA", "CN"]
    weights = [0.3, 0.25, 0.25, 0.2]  # US is slightly more likely, others even
    return random.choices(regions, weights=weights)[0]

def generate_game_timestamps(base_time, game_count):
    """Generate timestamps for multiple games of a player."""
    timestamps = []
    current_time = base_time
    for i in range(game_count):
        if i > 0:
            interval_minutes = random.randint(1, 60)
            current_time += timedelta(minutes=interval_minutes)
        timestamps.append(current_time)
    return timestamps

def generate_historical_stats_data(task_date: date, days_back=10, players_per_day=100):
    """Generate historical stats data (top 100 players of each of the last N days)."""
    historical_data = []

    print(f"📊 Generating historical statistics: past {days_back} days, {players_per_day} players per day")

    for day_offset in range(1, days_back + 1):
        target_date = task_date - timedelta(days=day_offset)
        print(f"   Generating data for {target_date} ...")

        day_players = []
        for rank in range(1, players_per_day + 1):
            base_skill = 95 - (rank - 1) * 0.5 + random.uniform(-5, 5)
            base_skill = max(20, min(95, base_skill))
            online_score = generate_realistic_score(base_skill, 1.0, 0.2) * random.randint(3, 8)
            task_score = generate_realistic_score(base_skill, 1.2, 0.25) * random.randint(2, 6)
            total_score = online_score + task_score
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
        day_players.sort(key=lambda x: x["total_score"], reverse=True)

        # Ensure all total_scores are unique by adjusting task_score
        seen_scores = set()
        for player in day_players:
            offset = 0
            while player["total_score"] in seen_scores:
                offset += 1
                player["total_task_score"] += 1
                player["total_score"] = player["total_online_score"] + player["total_task_score"]
            seen_scores.add(player["total_score"])

        # Re-sort after adjustments
        day_players.sort(key=lambda x: x["total_score"], reverse=True)
        historical_data.extend(day_players)

    print(f"✅ Generated {len(historical_data)} historical stats records")
    return historical_data

def setup_or_clear_dataset(client: bigquery.Client, project_id: str):
    """
    Set up or clear the existing game_analytics dataset.
    - If dataset exists: delete all tables in the dataset.
    - If dataset doesn't exist: create it (tables will be created later).
    """
    dataset_id = f"{project_id}.game_analytics"
    print(f"🧹 Checking and setting up dataset: {dataset_id}")

    try:
        try:
            dataset = client.get_dataset(dataset_id)
            print(f"ℹ️  Found existing dataset: {dataset_id}")

            tables = list(client.list_tables(dataset_id))
            if tables:
                print(f"ℹ️  Dataset contains {len(tables)} table(s):")
                for table in tables:
                    print(f"   - {table.table_id}")

                for table in tables:
                    table_id_fq = f"{dataset_id}.{table.table_id}"
                    print(f"🗑️  Deleting table {table.table_id}...")
                    client.delete_table(table_id_fq, not_found_ok=True)
                    print(f"✅ Deleted table {table.table_id}")
            else:
                print(f"ℹ️  Dataset is empty, nothing to clear")

        except NotFound:
            print(f"ℹ️  Dataset {dataset_id} does not exist, creating new dataset...")
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"
            dataset.description = "Game analytics dataset for daily scoring and leaderboards"
            client.create_dataset(dataset, timeout=30)
            print(f"✅ Dataset '{dataset.dataset_id}' created")

    except Exception as e:
        print(f"❌ Error while setting up dataset: {e}")
        logger.exception("Dataset setup failed")
        raise

def cleanup_existing_dataset(client: bigquery.Client, project_id: str):
    """
    Clean up existing game_analytics dataset if it exists.
    """
    dataset_id = f"{project_id}.game_analytics"
    print(f"🧹 Checking and cleaning existing dataset: {dataset_id}")

    try:
        try:
            dataset = client.get_dataset(dataset_id)
            print(f"ℹ️  Found existing dataset: {dataset_id}")

            tables = list(client.list_tables(dataset_id))
            if tables:
                print(f"ℹ️  Dataset contains {len(tables)} table(s):")
                for table in tables:
                    print(f"   - {table.table_id}")
        except NotFound:
            print(f"ℹ️  Dataset {dataset_id} does not exist, nothing to clean")
            return

        print(f"🗑️  Deleting dataset and all contents...")
        client.delete_dataset(
            dataset_id,
            delete_contents=True,
            not_found_ok=True
        )
        print(f"✅ Successfully cleaned dataset '{dataset_id}' and all its contents")

        import time
        time.sleep(2)

    except NotFound:
        print(f"ℹ️  Dataset {dataset_id} does not exist, nothing to clean")
    except Exception as e:
        print(f"❌ Error while cleaning dataset: {e}")
        logger.exception("Dataset cleanup failed")
        raise

def setup_bigquery_resources(credentials_path: str, project_id: str, task_date: date):
    """
    Setup BigQuery dataset and tables, then populate with sample data.
    """
    print("=" * 60)
    print("🎯 Starting BigQuery game statistics resource setup")
    print("=" * 60)

    try:
        print(f"🔗 Connecting to project '{project_id}' using credentials '{credentials_path}'...")

        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(credentials=credentials, project=project_id)

        print("✅ Connection successful!")

        print("🔍 Testing connection - listing datasets...")
        try:
            datasets = list(client.list_datasets())
            print(f"ℹ️  There are {len(datasets)} dataset(s) in the project")
            for dataset in datasets:
                print(f"   - {dataset.dataset_id}")
        except Exception as e:
            print(f"⚠️  Error while listing datasets: {e}")

        setup_or_clear_dataset(client, project_id)

        dataset_id = f"{project_id}.game_analytics"

        table_id_stream = f"{dataset_id}.daily_scores_stream"
        print(f"🗂️  Checking and creating table: {table_id_stream}")
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
            print(f"✅ Table '{table_id_stream}' created.")
        except Conflict:
            print(f"ℹ️  Table '{table_id_stream}' already exists, skipping creation.")
        except Exception as e:
            print(f"❌ Failed to create table '{table_id_stream}': {e}")
            raise

        table_id_stats = f"{dataset_id}.player_historical_stats"
        print(f"🗂️  Checking and creating table: {table_id_stats}")
        schema_stats = [
            bigquery.SchemaField("player_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("player_region", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("total_online_score", "INTEGER"),
            bigquery.SchemaField("total_task_score", "INTEGER"),
            bigquery.SchemaField("total_score", "INTEGER", description="Total score for the day (online + task)"),
            bigquery.SchemaField("game_count", "INTEGER"),
        ]
        table_stats = bigquery.Table(table_id_stats, schema=schema_stats)
        try:
            client.create_table(table_stats)
            print(f"✅ Table '{table_id_stats}' created.")
        except Conflict:
            print(f"ℹ️  Table '{table_id_stats}' already exists, skipping creation.")
        except Exception as e:
            print(f"❌ Failed to create table '{table_id_stats}': {e}")
            raise

        today = task_date
        today_str = today.isoformat()
        print(f"📈 Generating sample data for task date: {today_str}")

        sample_rows = []
        player_count = 200
        print(f"👥 Generating improved game data for {player_count} players...")

        player_skills = {}
        for player_id in range(1, player_count + 1):
            player_skills[player_id] = generate_player_skill_level()

        for player_id in range(1, player_count + 1):
            games_count = random.choices([3, 4, 5, 6, 7, 8, 9, 10],
                                       weights=[5, 10, 15, 20, 20, 15, 10, 5])[0]
            start_time = generate_safe_start_time(today, games_count)
            timestamps = generate_game_timestamps(start_time, games_count)
            player_skill = player_skills[player_id]
            player_region = get_realistic_region_distribution()

            for game_num in range(games_count):
                game_difficulty = random.uniform(0.8, 1.5)
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
        print(f"📝 Generated {len(sample_rows)} improved sample records")

        observed_dates = sorted({
            datetime.fromisoformat(row["timestamp"]).date().isoformat()
            for row in sample_rows
        })
        if observed_dates != [today_str]:
            raise ValueError(
                f"Generated spillover data outside task date {today_str}: {observed_dates}"
            )

        # Ensure each player's total score is unique
        print("🔍 Checking and adjusting for unique total scores per player...")
        player_totals = {}
        for row in sample_rows:
            pid = row["player_id"]
            if pid not in player_totals:
                player_totals[pid] = {"total_online": 0, "total_task": 0, "rows": []}
            player_totals[pid]["total_online"] += row["scores"]["online_score"]
            player_totals[pid]["total_task"] += row["scores"]["task_score"]
            player_totals[pid]["rows"].append(row)

        seen_totals = set()
        for pid, data in player_totals.items():
            total_score = data["total_online"] + data["total_task"]
            offset = 0
            while total_score in seen_totals:
                offset += 1
                total_score = data["total_online"] + data["total_task"] + offset

            # If we need to adjust, add the offset to the last game's task_score
            if offset > 0:
                last_row = data["rows"][-1]
                last_row["scores"]["task_score"] += offset
                print(f"   Adjusted {pid}: added {offset} to last game's task_score")

            seen_totals.add(total_score)

        print(f"💾 Inserting sample data into daily_scores_stream...")
        try:
            table_ref = client.get_table(table_id_stream)
            print(f"✅ Got table reference: {table_ref.table_id}")

            print("🔄 Using batch load to insert data...")
            job_config = bigquery.LoadJobConfig(
                write_disposition="WRITE_TRUNCATE",
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            )
            load_job = client.load_table_from_json(
                sample_rows, table_ref, job_config=job_config
            )
            print(f"   Started batch load job: {load_job.job_id}")
            load_job.result()  # Wait for completion

            print(f"🎉 Successfully loaded {len(sample_rows)} sample records to daily_scores_stream")

            print("🔍 Verifying data insertion...")
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
                print(f"✅ Verification successful: {result.total_rows} rows, {result.unique_players} unique players, date: {result.data_date}")
            else:
                print("⚠️  No result returned from verification query")
        except Exception as e:
            print(f"❌ Error inserting data: {e}")
            logger.exception("Data insertion failed")
            raise Exception(f"Failed to insert data: {e}")

        print(f"\n📈 Generating and inserting historical statistics data...")
        try:
            historical_data = generate_historical_stats_data(task_date=today, days_back=10, players_per_day=100)
            table_ref_stats = client.get_table(table_id_stats)
            print(f"💾 Inserting historical statistics data to player_historical_stats...")

            print("🔄 Using batch load to insert historical data...")
            job_config = bigquery.LoadJobConfig(
                write_disposition="WRITE_TRUNCATE",
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            )

            load_job = client.load_table_from_json(
                historical_data, table_ref_stats, job_config=job_config
            )
            print(f"   Started batch load job for historical data: {load_job.job_id}")
            load_job.result()

            print(f"🎉 Successfully loaded {len(historical_data)} historical statistics records to player_historical_stats")

            print("🔍 Verifying historical data insertion...")
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
                print(f"✅ Historical data verification succeeded: {result.total_rows} rows, {result.unique_dates} distinct dates")
                print(f"   Date range: {result.earliest_date} to {result.latest_date}")
            else:
                print("⚠️  No result returned from historical data verification query")
        except Exception as e:
            print(f"❌ Error inserting historical data: {e}")
            logger.exception("Historical data insertion failed")
            raise Exception(f"Failed to insert historical data: {e}")

        return client, dataset_id

    except GoogleAPICallError as e:
        print(f"❌ Google Cloud API call failed: {e}")
        logger.exception("Google Cloud API call failed")
        raise
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        logger.exception("Setup process failed")
        raise

def get_project_id_from_key(credentials_path: str) -> str | None:
    """Read project_id from a service account key file."""
    try:
        with open(credentials_path, 'r') as f:
            data = json.load(f)
            return data.get("project_id")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--credentials_file", default="configs/gcp-service_account.keys.json")
    parser.add_argument("--launch_time", required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()

    print("🎮 Starting BigQuery game statistics resource setup...")
    print("=" * 60)

    # Get credentials file path
    credentials_path = Path(args.credentials_file)

    # Make sure the path is absolute
    if not credentials_path.is_absolute():
        credentials_path = Path.cwd() / credentials_path

    if not credentials_path.exists():
        print(f"❌ Error: Credentials file does not exist: {credentials_path}")
        print("Please make sure the service account key file exists at the specified path")
        exit(1)
    else:
        print(f"✅ Credentials file found: {credentials_path}")

    project_id = get_project_id_from_key(str(credentials_path))

    try:
        task_date = parse_task_date(args.launch_time)
    except ValueError as e:
        print(f"❌ {e}")
        exit(1)

    try:
        save_task_date(task_date, args.agent_workspace)
    except OSError as e:
        print(f"❌ {e}")
        exit(1)

    if project_id:
        print(f"🆔 Project ID successfully read from credentials file: {project_id}")
        try:
            client, dataset_id = setup_bigquery_resources(str(credentials_path), project_id, task_date)
            print("\n" + "=" * 60)
            print("🎉 All BigQuery resources have been set up!")
            print("📊 Sample game data for today has been generated")
            print("🎯 Task: The agent should generate leaderboards and update historical statistics")
            print("=" * 60)
        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            exit(1)
    else:
        print(f"❌ Could not read project_id from credentials file.")
        exit(1)