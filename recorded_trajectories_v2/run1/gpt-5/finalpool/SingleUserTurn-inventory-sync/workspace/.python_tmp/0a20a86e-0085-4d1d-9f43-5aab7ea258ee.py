import sqlite3, os, json, datetime, pathlib
base = "/ssddata/junlong/projects/mcpbench_finalpool_dev/recorded_trajectories_v2/run1/gpt-5/finalpool/SingleUserTurn-inventory-sync/workspace/warehouse"
files = [
    ("Boston", os.path.join(base,"warehouse_boston.db")),
    ("Dallas", os.path.join(base,"warehouse_dallas.db")),
    ("Houston", os.path.join(base,"warehouse_houston.db")),
    ("Los Angeles", os.path.join(base,"warehouse_los_angeles.db")),
    ("New York", os.path.join(base,"warehouse_new_york.db")),
    ("San Francisco", os.path.join(base,"warehouse_san_francisco.db")),
]

now = datetime.datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
updated_counts = {}
for city, path in files:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("UPDATE inventory SET sync_status='synced', sync_timestamp=? WHERE sync_status='pending'", (now,))
    updated_counts[city] = cur.rowcount
    conn.commit()
    conn.close()

report = {
    "synced_at": now,
    "updated_rows_per_city": updated_counts,
}

report_path = "/ssddata/junlong/projects/mcpbench_finalpool_dev/recorded_trajectories_v2/run1/gpt-5/finalpool/SingleUserTurn-inventory-sync/workspace/sync_report.json"
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
print("REPORT_PATH=", report_path)
