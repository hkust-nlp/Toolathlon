import sqlite3, os, json
base = "/ssddata/junlong/projects/mcpbench_finalpool_dev/recorded_trajectories_v2/run1/gpt-5/finalpool/SingleUserTurn-inventory-sync/workspace"
warehouse_dir = os.path.join(base, "warehouse")
report_path = os.path.join(base, "sync_report.json")
with open(report_path, 'r') as f:
    base_report = json.load(f)
synced_at = base_report["synced_at"]

files = [
    ("Boston", os.path.join(warehouse_dir,"warehouse_boston.db")),
    ("Dallas", os.path.join(warehouse_dir,"warehouse_dallas.db")),
    ("Houston", os.path.join(warehouse_dir,"warehouse_houston.db")),
    ("Los Angeles", os.path.join(warehouse_dir,"warehouse_los_angeles.db")),
    ("New York", os.path.join(warehouse_dir,"warehouse_new_york.db")),
    ("San Francisco", os.path.join(warehouse_dir,"warehouse_san_francisco.db")),
]

region_of_city = {}
per_city_synced = {}
agg_by_region = {}

for city, path in files:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT region FROM warehouses LIMIT 1")
    region = cur.fetchone()[0]
    region_of_city[city] = region
    cur.execute("SELECT product_id, quantity FROM inventory WHERE sync_status='synced' AND sync_timestamp=?", (synced_at,))
    rows = cur.fetchall()
    per_city_synced[city] = {pid: qty for pid, qty in rows}
    for pid, qty in rows:
        agg_by_region.setdefault(pid, {}).setdefault(region, 0)
        agg_by_region[pid][region] += qty
    conn.close()

for pid in list(agg_by_region.keys()):
    for region in ["East","South","West"]:
        agg_by_region[pid].setdefault(region, 0)

totals_all = {pid: sum(reg.values()) for pid, reg in agg_by_region.items()}

full_report = {
    **base_report,
    "region_of_city": region_of_city,
    "per_city_synced": per_city_synced,
    "agg_by_region": agg_by_region,
    "totals_all": totals_all,
}

out_path = os.path.join(base, "sync_detailed_report.json")
with open(out_path, 'w') as f:
    json.dump(full_report, f, indent=2)

print("DETAILED_REPORT_PATH=", out_path)
print(json.dumps(full_report, indent=2))
