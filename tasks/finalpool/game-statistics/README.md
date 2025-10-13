Data Generation Method:

  1. Table: daily_scores_stream
    - 200 virtual players
    - Each player has 3-10 game records
    - Scores are generated based on player skill level for realistic distribution
    - Includes two score fields: online_score and task_score
  2. Table: player_historical_stats
    - Historical data for the past 10 days
    - 100 player statistics records each day
    - Fields include: player_id, date, total_score, game_count, etc.

The evaluation for this task consists of two main checks:

  1. Daily Leaderboard Verification (verify_daily_leaderboard)

  Check Details:
  - Table name format: leaderboard_YYYYMMDD (e.g., leaderboard_20250804)
  - Data volume: Must contain exactly 100 records
  - Sorting: Sorted by total_score in descending order
  - Ranking: The rank field must be consecutive from 1 to 100

  Fields to Verify:
  - player_id: Player ID
  - total_score: Total score
  - rank: Rank (must be consecutive 1-100)

  2. Historical Statistics Update Verification (verify_historical_stats_update)

  Check Details:
  - Table name: player_historical_stats
  - Data consistency: Compare against original data in daily_scores_stream
  - Aggregation accuracy: Verify each player’s total score and game count

  Verification Logic:
  - Aggregate same-day data from daily_scores_stream: SUM(scores.online_score + scores.task_score)
  - Compare each record with the corresponding entry in player_historical_stats
  - Check the accuracy of total_score and game_count fields

  Only verify today’s data:
  -- evaluation/main.py:88-94: Only queries today
  WHERE date = '{today_str}'

  -- evaluation/main.py:118-122: Only queries today as well  
  WHERE DATE(timestamp) = '{today_str}'

  One record per player per day:
  From the structure of player_historical_stats:
  - (player_id, date) forms a composite primary key
  - Each player has only one record per day
  - Records for different dates are independent and not merged

  Verification Logic:
  - For today, aggregate all game records for each player from daily_scores_stream
  - Group by player_id to obtain total score and game count for the day
  - Compare with the corresponding records in player_historical_stats for today
  - Ensure that each player’s total score and game count match between the two tables