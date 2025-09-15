import sqlite3, json, os, sys
from pathlib import Path

base = "/ssddata/junlong/projects/mcpbench_finalpool_dev/recorded_trajectories_v2/run1/gpt-5/finalpool/SingleUserTurn-inventory-sync/workspace/warehouse"
files = [
    "warehouse_boston.db",
    "warehouse_dallas.db",
    "warehouse_houston.db",
    "warehouse_los_angeles.db",
    "warehouse_new_york.db",
    "warehouse_san_francisco.db",
]

def inspect_db(path):
    out = {"path": path, "tables": {}, "errors": None}
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            cur.execute(f"PRAGMA table_info({t});")
            cols = cur.fetchall()
            out["tables"][t] = {
                "columns": [{"cid": c[0], "name": c[1], "type": c[2], "notnull": c[3], "dflt": c[4], "pk": c[5]} for c in cols]
            }
            # sample rows
            cur.execute(f"SELECT * FROM {t} LIMIT 5;")
            rows = cur.fetchall()
            out["tables"][t]["sample_rows"] = rows
        conn.close()
    except Exception as e:
        out["errors"] = str(e)
    return out

results = [inspect_db(os.path.join(base,f)) for f in files]
print(json.dumps(results, indent=2))
