import sqlite3, os, json, datetime
base = "/ssddata/junlong/projects/mcpbench_finalpool_dev/recorded_trajectories_v2/run1/gpt-5/finalpool/SingleUserTurn-inventory-sync/workspace/warehouse"
files = [
    ("Boston", os.path.join(base,"warehouse_boston.db")),
    ("Dallas", os.path.join(base,"warehouse_dallas.db")),
    ("Houston", os.path.join(base,"warehouse_houston.db")),
    ("Los Angeles", os.path.join(base,"warehouse_los_angeles.db")),
    ("New York", os.path.join(base,"warehouse_new_york.db")),
    ("San Francisco", os.path.join(base,"warehouse_san_francisco.db")),
]

city_key_map = {
    "Boston":"boston",
    "Dallas":"dallas",
    "Houston":"houston",
    "Los Angeles":"los_angeles",
    "New York":"new_york",
    "San Francisco":"san_francisco",
}

region_of_city = {}
per_city_pending = {}
agg_by_region = {}

for city, path in files:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    # get region info from warehouses table
    cur.execute("SELECT region FROM warehouses LIMIT 1")
    region = cur.fetchone()[0]
    region_of_city[city] = region
    # query pending inventory and quantities
    cur.execute("SELECT product_id, quantity FROM inventory WHERE sync_status='pending'")
    rows = cur.fetchall()
    per_city_pending[city] = {pid:qty for pid,qty in rows}
    # aggregate into agg_by_region
    for pid, qty in rows:
        agg_by_region.setdefault(pid, {}).setdefault(region, 0)
        agg_by_region[pid][region] += qty
    conn.close()

# Ensure regions keys exist
for pid in list(agg_by_region.keys()):
    for region in ["East","South","West"]:
        agg_by_region[pid].setdefault(region, 0)

# Also compute grand totals
totals_all = {pid: sum(reg.values()) for pid, reg in agg_by_region.items()}

print(json.dumps({
    "region_of_city": region_of_city,
    "per_city_pending": per_city_pending,
    "agg_by_region": agg_by_region,
    "totals_all": totals_all,
}, indent=2))
