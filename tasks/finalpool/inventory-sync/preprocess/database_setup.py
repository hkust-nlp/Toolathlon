import sqlite3
import os
import random
from datetime import datetime, timedelta
from os import sys, path

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
initial_workspace_dir = os.path.join(task_dir, "initial_workspace")
sys.path.append(initial_workspace_dir)

# 城市和区域映射
CITY_REGION_MAPPING = {
    # East区域
    "New York": "East",
    "Boston": "East", 
    
    # South区域
    "Dallas": "South",
    "Houston": "South",
    
    # West区域
    "LA": "West",
    "San Francisco": "West"
}

# 英文城市名映射（用于数据库文件名）
CITY_NAME_MAPPING = {
    "New York": "new_york",
    "Boston": "boston",
    "Dallas": "dallas",
    "Houston": "houston",
    "LA": "los_angeles",
    "San Francisco": "san_francisco"
}

# 动态获取数据库文件夹路径
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
DB_FOLDER = os.path.join(task_dir, "initial_workspace", "warehouse")


def clear_all_databases():
    # 确保数据库文件夹存在
    os.makedirs(DB_FOLDER, exist_ok=True)
    
    for filename in os.listdir(DB_FOLDER):
        if filename.endswith(".db"):
            os.remove(os.path.join(DB_FOLDER, filename))

def create_warehouse_database(city_name_cn, city_name_en):
    """为每个城市创建仓库数据库"""
    # 确保数据库文件夹存在
    os.makedirs(DB_FOLDER, exist_ok=True)
    
    db_path = f"{DB_FOLDER}/warehouse_{city_name_en}.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建仓库信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warehouses (
            warehouse_id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_name_cn TEXT NOT NULL,
            city_name_en TEXT NOT NULL,
            region TEXT NOT NULL,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建商品表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT,
            price DECIMAL(10,2),
            description TEXT,
            publish_date TIMESTAMP,  -- Released Time
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建库存表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            warehouse_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            total_sales INTEGER NOT NULL DEFAULT 0,  -- Total Sales
            monthly_sales INTEGER NOT NULL DEFAULT 0,  -- Monthly Sales
            sales_last_30_days INTEGER NOT NULL DEFAULT 0,  -- Sales Last 30 Days
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_status TEXT DEFAULT 'pending',  -- pending, synced, failed
            sync_timestamp TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (product_id),
            FOREIGN KEY (warehouse_id) REFERENCES warehouses (warehouse_id)
        )
    ''')
    
    # 创建库存变更日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            warehouse_id INTEGER NOT NULL,
            old_quantity INTEGER,
            new_quantity INTEGER,
            change_type TEXT,  -- restock, sale, adjustment, sync
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (product_id),
            FOREIGN KEY (warehouse_id) REFERENCES warehouses (warehouse_id)
        )
    ''')
    
    # 插入仓库信息
    cursor.execute('''
        INSERT OR REPLACE INTO warehouses (warehouse_id, city_name_cn, city_name_en, region, address)
        VALUES (1, ?, ?, ?, ?)
    ''', (city_name_cn, city_name_en, CITY_REGION_MAPPING[city_name_cn], f"{city_name_cn}市中心仓库区"))
    
    conn.commit()
    conn.close()
    
    print(f"✓ 创建了 {city_name_cn} ({city_name_en}) 的仓库数据库: {db_path}")
    return db_path

def generate_sample_products():
    """生成示例商品数据"""
    products = [
        ("PROD001", "iPhone 15 Pro", "Electronic Products ", 999.99, "iPhone 17"),
        ("PROD002", "MacBook Air M2", "Electronic Products ", 1299.99, "Lightweight Laptop"),
        ("PROD003", "AirPods Pro", "Electronic Products ", 249.99, "Noise-cancelling Earbuds"),
        ("PROD004", "iPad Air", "Electronic Products ", 599.99, "iPad Mini"),
        ("PROD005", "Apple Watch Series 9", "Electronic Products ", 399.99, "iWatch")
    ]
    return products

def populate_database_with_sample_data(city_name_cn, city_name_en):
    """为数据库填充示例数据"""
    db_path = f"{DB_FOLDER}/warehouse_{city_name_en}.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 插入商品数据
    products = generate_sample_products()
    cursor.executemany('''
        INSERT OR REPLACE INTO products (product_id, product_name, category, price, description)
        VALUES (?, ?, ?, ?, ?)
    ''', products)
    
    # 为每个商品生成随机库存
    for product_id, _, _, _, _ in products:
        # 根据城市规模生成不同的库存数量
        if city_name_cn in ["New York", "LA", "Dallas", "Houston"]:  # 大城市
            base_quantity = random.randint(200, 800)
        elif city_name_cn in ["Boston", "San Francisco"]:  # 中等城市
            base_quantity = random.randint(150, 600)
        else:  # 其他城市
            base_quantity = random.randint(100, 400)
            
        cursor.execute('''
            INSERT OR REPLACE INTO inventory 
            (product_id, warehouse_id, quantity)
            VALUES (?, 1, ?)
        ''', (product_id, base_quantity))
        
        # 添加一些库存变更日志
        for _ in range(random.randint(1, 3)):
            old_qty = random.randint(0, base_quantity)
            new_qty = random.randint(0, base_quantity + 100)
            change_type = random.choice(['restock', 'sale', 'adjustment'])
            log_date = datetime.now() - timedelta(days=random.randint(1, 30))
            
            cursor.execute('''
                INSERT INTO inventory_logs 
                (product_id, warehouse_id, old_quantity, new_quantity, change_type, created_at)
                VALUES (?, 1, ?, ?, ?, ?)
            ''', (product_id, old_qty, new_qty, change_type, log_date))
    
    conn.commit()
    conn.close()
    
    print(f"✓ 为 {city_name_cn} 数据库填充了示例数据")

def create_all_warehouse_databases():
    """创建所有城市的仓库数据库"""
    print("开始创建多城市仓库数据库...")
    
    created_databases = []
    
    for city_cn, city_en in CITY_NAME_MAPPING.items():
        db_path = create_warehouse_database(city_cn, city_en)
        populate_database_with_sample_data(city_cn, city_en)
        created_databases.append(db_path)
    
    print(f"\n✅ 成功创建了 {len(created_databases)} 个城市的仓库数据库:")
    for db in created_databases:
        print(f"  - {db}")
    
    return created_databases

if __name__ == "__main__":
    clear_all_databases()
    # 创建所有数据库
    create_all_warehouse_databases()
    print("\n🎉 数据库初始化完成！")
    print("📝 下一步可以运行库存同步程序来测试WooCommerce集成。")
