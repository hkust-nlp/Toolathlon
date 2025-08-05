# Let's get all the columns for player_historical_stats table
from google.cloud import bigquery

client = bigquery.Client()

query = """
SELECT 
  column_name, 
  data_type,
  ordinal_position
FROM `game_analytics.INFORMATION_SCHEMA.COLUMNS` 
WHERE table_name = 'player_historical_stats' 
ORDER BY ordinal_position
"""

query_job = client.query(query)
results = query_job.result()

print("Columns in player_historical_stats table:")
for row in results:
    print(f"{row.ordinal_position}: {row.column_name} ({row.data_type})")