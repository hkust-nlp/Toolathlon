#!/usr/bin/env python3
"""
Snowflake Database Initialization Script
使用MCP Snowflake服务器来初始化供应商发票对账系统的数据库
"""

import argparse
import asyncio
import importlib.util
import json
import os
import random
import sys
from rich import print
from rich.console import Console
from rich.table import Table

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up: preprocess -> payable-invoice-checker -> fan -> tasks -> mcpbench_dev
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)
try:
    from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry
except ImportError as e:
    print(f"Import error: {e}")
    print("Please run from the project root directory or ensure the project structure is correct")
    sys.exit(1)

# 导入测试发票生成模块
from . import generate_test_invoices

# 导入任务特定的配置用于覆盖
# 添加父目录到路径并导入
local_token_key_session_file = os.path.join(os.path.dirname(__file__), "..", "token_key_session.py")
try:
    # from local_token_key_session import all_token_key_session as local_token_key_session
    # 用importlib.util来从文件路径导入模块
    spec = importlib.util.spec_from_file_location("token_key_session", local_token_key_session_file)
    token_key_session_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(token_key_session_module)
    local_token_key_session = token_key_session_module.all_token_key_session
except ImportError:
    print("警告: 未找到任务特定的 token_key_session.py，将使用默认配置")
    local_token_key_session = {
        "snowflake_op_allowed_databases": "PURCHASE_INVOICE",
    }

console = Console()


def display_table_structure():
    """显示要创建的表结构"""
    print("\n" + "="*60)
    print("📋 DATABASE SCHEMA DESIGN")
    print("="*60)
    
    # Invoices table structure
    invoices_table = Table(title="INVOICES Table Structure")
    invoices_table.add_column("Column", style="cyan")
    invoices_table.add_column("Type", style="magenta")
    invoices_table.add_column("Description", style="green")
    
    invoices_table.add_row("INVOICE_ID", "VARCHAR(100)", "发票号（主键，带格式）")
    invoices_table.add_row("SUPPLIER_NAME", "VARCHAR(500)", "供应商名称")
    invoices_table.add_row("INVOICE_AMOUNT", "DECIMAL(15,2)", "发票金额")
    invoices_table.add_row("PURCHASER_EMAIL", "VARCHAR(255)", "采购负责人邮箱")
    invoices_table.add_row("INVOICE_DATE", "DATE", "发票日期")
    
    console.print(invoices_table)
    
    # Payments table structure  
    payments_table = Table(title="INVOICE_PAYMENTS Table Structure")
    payments_table.add_column("Column", style="cyan")
    payments_table.add_column("Type", style="magenta") 
    payments_table.add_column("Description", style="green")
    
    payments_table.add_row("INVOICE_ID", "VARCHAR(100)", "发票号（主键，外键）")
    payments_table.add_row("PAYMENT_AMOUNT", "DECIMAL(15,2)", "已付金额")
    payments_table.add_row("OUTSTANDING_FLAG", "INTEGER", "未清标记（1=未清，0=已清）")
    
    console.print(payments_table)


async def execute_sql(server, sql_query: str, description: str = "", tool_type: str = "write"):
    """执行SQL查询"""
    try:
        if description:
            print(f"🔄 {description}")
        
        # 根据SQL类型选择合适的工具
        if tool_type == "create":
            tool_name = "create_table"
            arguments = {"query": sql_query}
        elif tool_type == "read":
            tool_name = "read_query"
            arguments = {"query": sql_query}
        else:  # write operations (INSERT, UPDATE, DELETE, DROP, etc.)
            tool_name = "write_query"
            arguments = {"query": sql_query}
        
        # 调用MCP工具执行SQL
        result = await call_tool_with_retry(
            server,
            tool_name=tool_name,
            arguments=arguments
        )
        
        print(f"✅ {description or 'SQL executed successfully'}")
        if hasattr(result, 'content') and result.content:
            # 尝试不同的结果访问方式
            if hasattr(result.content[0], 'text'):
                print(f"   Result: {result.content[0].text}")
            elif hasattr(result.content[0], 'content'):
                print(f"   Result: {result.content[0].content}")
        return True
        
    except Exception as e:
        print(f"❌ Error executing SQL ({description}): {e}")
        return False


async def generate_invoice_data():
    """生成测试发票数据"""
    invoices_data = []

    supplier_types = list(generate_test_invoices.SUPPLIERS_CONFIG.keys())

    # 使用全局发票ID集合，确保与真实发票不冲突
    def generate_unique_invoice_id(year, prefix_type="interference"):
        """生成唯一的发票ID"""
        max_attempts = 1000  # 防止无限循环
        attempt = 0

        while attempt < max_attempts:
            if prefix_type == "interference":
                # 干扰数据使用多种格式，但确保唯一性
                interference_formats = [
                    f"INT-{year}-{random.randint(1, 2000):04d}",
                    f"NOISE-{random.randint(10000, 99999)}",
                    f"FAKE-{random.randint(100000, 999999)}",
                    f"TEST{random.randint(1000, 9999)}-{year}",
                    f"DIST-{year}-{random.randint(100, 999)}"
                ]
                invoice_id = random.choice(interference_formats)
            else:
                # 真实发票格式
                real_formats = [
                    f"INV-2024-{random.randint(1, 2000):03d}",
                    f"2024-{random.randint(1000, 9999)}",
                    f"MCP-{random.randint(100000, 999999)}",
                    f"PO{random.randint(10000, 99999)}-24",
                    f"BL-2024-{random.randint(100, 999)}",
                    f"REF{random.randint(1000, 9999)}24",
                    f"INV{random.randint(100000, 999999)}"
                ]
                invoice_id = random.choice(real_formats)

            # 检查是否已存在于全局集合中
            if invoice_id not in generate_test_invoices.USED_INVOICE_IDS:
                generate_test_invoices.USED_INVOICE_IDS.add(invoice_id)
                return invoice_id

            attempt += 1

        # 如果尝试多次仍无法生成唯一ID，使用时间戳确保唯一性
        import time
        timestamp = int(time.time() * 1000)
        unique_id = f"UNIQUE-{timestamp}-{random.randint(1000, 9999)}"
        generate_test_invoices.USED_INVOICE_IDS.add(unique_id)
        return unique_id

    # 干扰数据使用专门的邮箱列表，避免与groundtruth邮箱重复
    interference_buyer_emails = [
        "JSmith@mcp.com",
        "MBrown@mcp.com",
        "AWilliams@mcp.com",
        "RJohnson@mcp.com",
        "LDavis@mcp.com",
        "KWilson@mcp.com",
        "TMiller@mcp.com",
        "SAnderson@mcp.com"
    ]

    # 先生成干扰数据（1000条），使用更早的日期
    print("🎭 生成干扰数据 (1000条)...")
    for i in range(1, 1001):  # 1000条干扰数据
        supplier_type = generate_test_invoices.random.choice(supplier_types)
        supplier_config = generate_test_invoices.SUPPLIERS_CONFIG[supplier_type]
        buyer_email = generate_test_invoices.random.choice(interference_buyer_emails)

        # 生成项目和总金额
        items = generate_test_invoices.generate_invoice_items(supplier_type)
        total_amount = sum(item['total'] for item in items)

        # 干扰数据：全部设置为已付清状态
        payment_status = {
            "paid_amount": total_amount,  # 已付金额等于发票金额
            "status": "paid",            # 状态为已支付
            "flag": 0,                   # 未清标记为0（已清）
            "show_status": True
        }

        # 生成更早的日期 (2022-2023年)
        year = generate_test_invoices.random.choice([2022, 2023])
        month = generate_test_invoices.random.randint(1, 12)
        day = generate_test_invoices.random.randint(1, 28)
        date_str = f"{year}-{month:02d}-{day:02d}"

        # 生成独特的干扰数据发票号，确保唯一性
        invoice_id = generate_unique_invoice_id(year, "interference")

        invoice_data = {
            "invoice_number": invoice_id,
            "supplier_name": supplier_config["name"],
            "invoice_amount": total_amount,
            "purchaser_email": buyer_email,
            "invoice_date": date_str,
            "paid_amount": payment_status["paid_amount"],  # 等于total_amount
            "outstanding_flag": payment_status["flag"],    # 0表示已付清
            "is_interference": True  # 标记为干扰数据
        }

        invoices_data.append(invoice_data)

    # 预先生成16个真实发票的ID，确保不与干扰数据冲突
    print("🎯 预先生成16个真实发票ID，确保唯一性...")
    for i in range(1, 17):  # 16个真实发票
        real_invoice_id = generate_unique_invoice_id(2024, "real")
        print(f"预生成真实发票ID: {real_invoice_id}")

    print(f"✅ 已预生成16个唯一真实发票ID，当前全局ID总数: {len(generate_test_invoices.USED_INVOICE_IDS)}")

    # 跳过原始数据生成，让agent从PDF中读取
    print("🚫 跳过原始数据生成 - 将由agent从PDF中读取")

    # 对所有数据按日期排序（总体递增，但允许一定程度的打乱）
    invoices_data.sort(key=lambda x: x['invoice_date'])

    # 对排序后的数据进行轻微打乱（保持总体递增趋势）
    random.seed(42)  # 保证可重现性

    # 每10条数据中随机交换少数几条，保持总体递增
    for i in range(0, len(invoices_data) - 10, 10):
        end_idx = min(i + 10, len(invoices_data))
        chunk = invoices_data[i:end_idx]

        # 随机交换2-3对位置
        for _ in range(random.randint(2, 3)):
            if len(chunk) >= 2:
                idx1, idx2 = random.sample(range(len(chunk)), 2)
                chunk[idx1], chunk[idx2] = chunk[idx2], chunk[idx1]

        invoices_data[i:end_idx] = chunk

    print(f"✅ 生成了 {len(invoices_data)} 条干扰数据")

    # 导出干扰数据到groundtruth_workspace
    await export_interference_data(invoices_data)

    return invoices_data

async def export_interference_data(invoices_data):
    """导出干扰数据到groundtruth_workspace目录"""
    print("🎭 导出干扰数据...")

    # 创建输出目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    task_root = os.path.dirname(current_dir)
    output_dir = os.path.join(task_root, "groundtruth_workspace")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 所有数据都是干扰数据
    interference_data = invoices_data

    print(f"📊 干扰数据: {len(interference_data)} 条")

    # 导出干扰数据 - INVOICES格式
    if interference_data:
        invoices_file = os.path.join(output_dir, "interference_invoices.jsonl")
        with open(invoices_file, 'w', encoding='utf-8') as f:
            for item in interference_data:
                invoice_record = {
                    "invoice_id": item["invoice_number"],
                    "supplier_name": item["supplier_name"],
                    "invoice_amount": item["invoice_amount"],
                    "purchaser_email": item["purchaser_email"],
                    "invoice_date": item["invoice_date"]
                }
                f.write(json.dumps(invoice_record, ensure_ascii=False) + '\n')

        print(f"✅ 导出干扰发票数据: {invoices_file}")

    # 导出干扰数据 - INVOICE_PAYMENTS格式
    if interference_data:
        payments_file = os.path.join(output_dir, "interference_payments.jsonl")
        with open(payments_file, 'w', encoding='utf-8') as f:
            for item in interference_data:
                payment_record = {
                    "invoice_id": item["invoice_number"],
                    "payment_amount": item["paid_amount"],  # 等于total_amount
                    "outstanding_flag": item["outstanding_flag"]  # 0表示已付清
                }
                f.write(json.dumps(payment_record, ensure_ascii=False) + '\n')

        print(f"✅ 导出干扰支付数据: {payments_file}")

    print(f"🎭 干扰数据导出完成，共 {len(interference_data)} 条记录")


async def export_database_to_jsonl():
    """将数据库内容导出到JSONL文件"""
    print("📤 DATABASE EXPORT TO JSONL")
    print("=" * 60)
    print("Database: PURCHASE_INVOICE")
    print("Schema: PUBLIC")
    print("Purpose: Export database content to groundtruth workspace")

    # 创建MCP服务器管理器
    mcp_manager = MCPServerManager(
        agent_workspace="./",
        config_dir="configs/mcp_servers",
        local_token_key_session=local_token_key_session
    )

    try:
        # 获取Snowflake服务器
        snowflake_server = mcp_manager.servers['snowflake']

        async with snowflake_server as server:
            # 查询INVOICES表
            print("\n📋 Exporting INVOICES table...")
            invoices_query = """
            SELECT
                INVOICE_ID,
                SUPPLIER_NAME,
                INVOICE_AMOUNT,
                PURCHASER_EMAIL,
                INVOICE_DATE
            FROM PURCHASE_INVOICE.PUBLIC.INVOICES
            ORDER BY INVOICE_ID;
            """

            invoices_result = await execute_sql(
                server,
                invoices_query,
                "Querying INVOICES table for export",
                "read"
            )

            # 查询INVOICE_PAYMENTS表
            print("\n📋 Exporting INVOICE_PAYMENTS table...")
            payments_query = """
            SELECT
                INVOICE_ID,
                PAYMENT_AMOUNT,
                OUTSTANDING_FLAG
            FROM PURCHASE_INVOICE.PUBLIC.INVOICE_PAYMENTS
            ORDER BY INVOICE_ID;
            """

            payments_result = await execute_sql(
                server,
                payments_query,
                "Querying INVOICE_PAYMENTS table for export",
                "read"
            )

            # 创建输出目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            task_root = os.path.dirname(current_dir)
            output_dir = os.path.join(task_root, "groundtruth_workspace")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 解析并导出INVOICES数据
            if invoices_result:
                print("\n💾 Exporting INVOICES data to JSONL...")
                invoices_file = os.path.join(output_dir, "db_invoices.jsonl")

                with open(invoices_file, 'w', encoding='utf-8') as f:
                    lines = invoices_result.strip().split('\n')
                    if len(lines) > 2:  # 跳过表头和分隔符
                        data_lines = [line for line in lines[2:] if line.strip() and not line.startswith('---')]

                        for line in data_lines:
                            parts = [part.strip() for part in line.split('|') if part.strip()]
                            if len(parts) >= 5:
                                invoice_record = {
                                    "invoice_id": parts[0],
                                    "supplier_name": parts[1],
                                    "invoice_amount": float(parts[2]) if parts[2] else 0.0,
                                    "purchaser_email": parts[3],
                                    "invoice_date": parts[4]
                                }
                                f.write(json.dumps(invoice_record, ensure_ascii=False) + '\n')

                print(f"✅ Exported INVOICES data to: {invoices_file}")

            # 解析并导出INVOICE_PAYMENTS数据
            if payments_result:
                print("\n💾 Exporting INVOICE_PAYMENTS data to JSONL...")
                payments_file = os.path.join(output_dir, "db_payments.jsonl")

                with open(payments_file, 'w', encoding='utf-8') as f:
                    lines = payments_result.strip().split('\n')
                    if len(lines) > 2:  # 跳过表头和分隔符
                        data_lines = [line for line in lines[2:] if line.strip() and not line.startswith('---')]

                        for line in data_lines:
                            parts = [part.strip() for part in line.split('|') if part.strip()]
                            if len(parts) >= 3:
                                payment_record = {
                                    "invoice_id": parts[0],
                                    "payment_amount": float(parts[1]) if parts[1] else 0.0,
                                    "outstanding_flag": int(parts[2]) if parts[2] else 0
                                }
                                f.write(json.dumps(payment_record, ensure_ascii=False) + '\n')

                print(f"✅ Exported INVOICE_PAYMENTS data to: {payments_file}")


            print("\n🎉 DATABASE EXPORT COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("📁 Files exported to groundtruth_workspace/:")
            if invoices_result:
                print("   • db_invoices.jsonl - INVOICES table data (interference only)")
            if payments_result:
                print("   • db_payments.jsonl - INVOICE_PAYMENTS table data (interference only)")

    except Exception as e:
        print(f"❌ Database export failed: {e}")
        return False

    return True


async def initialize_database():
    """初始化数据库的主要逻辑"""
    print("🏦 SNOWFLAKE DATABASE INITIALIZATION")
    print("=" * 60)
    print("Database: PURCHASE_INVOICE")
    print("Schema: PUBLIC")
    print("Purpose: 供应商发票对账系统")

    # 显示表结构设计
    display_table_structure()
    
    # 创建MCP服务器管理器
    mcp_manager = MCPServerManager(
        agent_workspace="./",
        config_dir="configs/mcp_servers",
        local_token_key_session=local_token_key_session
    )
    
    try:
        # 获取Snowflake服务器
        snowflake_server = mcp_manager.servers['snowflake']
        
        # 连接到服务器
        async with snowflake_server as server:
            print("\n" + "="*60)
            print("🚀 EXECUTING DATABASE INITIALIZATION")
            print("="*60)
            
            # Skip session setup - use fully qualified names instead
            
            # 1. 直接drop原来的数据库（如有) 然后新建新的数据库
            # 1.1 check if the database exists
            check_database_sql = "SELECT EXISTS(SELECT 1 FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = 'PURCHASE_INVOICE');"
            database_exists = await execute_sql(server, check_database_sql, "Checking if database exists", "read")
            if database_exists:
                print("\n📋 Step 0: Dropping existing database...")
                await call_tool_with_retry(server, tool_name="drop_databases", arguments={"databases": ["PURCHASE_INVOICE"]})

            print("\n📋 Step 1: Creating new database...")
            await call_tool_with_retry(server, tool_name="create_databases", arguments={"databases": ["PURCHASE_INVOICE"]})
            
            # 2. 创建发票表
            print("\n📋 Step 2: Creating INVOICES table...")
            create_invoices_sql = """
            CREATE TABLE PURCHASE_INVOICE.PUBLIC.INVOICES (
                INVOICE_ID VARCHAR(100) PRIMARY KEY,
                SUPPLIER_NAME VARCHAR(500) NOT NULL,
                INVOICE_AMOUNT DECIMAL(15,2) NOT NULL,
                PURCHASER_EMAIL VARCHAR(255) NOT NULL,
                INVOICE_DATE DATE
            );"""
            
            await execute_sql(server, create_invoices_sql, "Creating INVOICES table", "create")
            
            # 3. 创建付款表
            print("\n📋 Step 3: Creating INVOICE_PAYMENTS table...")
            create_payments_sql = """
            CREATE TABLE PURCHASE_INVOICE.PUBLIC.INVOICE_PAYMENTS (
                INVOICE_ID VARCHAR(100) PRIMARY KEY,
                PAYMENT_AMOUNT DECIMAL(15,2) DEFAULT 0.00,
                OUTSTANDING_FLAG INTEGER DEFAULT 1,
                FOREIGN KEY (INVOICE_ID) REFERENCES PURCHASE_INVOICE.PUBLIC.INVOICES(INVOICE_ID)
            );"""
            
            await execute_sql(server, create_payments_sql, "Creating INVOICE_PAYMENTS table", "create")
            
            # 4. 插入生成的测试数据
            print("\n📋 Step 4: Generating and inserting test data...")
            
            # 生成测试发票数据
            invoices_data = await generate_invoice_data()
            print(f"Generated {len(invoices_data)} test invoices")
            
            # 批量插入发票数据 - 使用单次批量插入优化性能
            print(f"📦 批量插入 {len(invoices_data)} 条发票数据...")

            # 构建批量INSERT语句
            values_list = []
            for invoice in invoices_data:
                # 处理supplier_name中的单引号
                supplier_name = invoice['supplier_name'].replace("'", "''")
                values_list.append(f"('{invoice['invoice_number']}', '{supplier_name}', {invoice['invoice_amount']:.2f}, '{invoice['purchaser_email']}', '{invoice['invoice_date']}')")

            # 批量INSERT - 减少网络往返
            batch_size = 100  # 每批100条记录
            for i in range(0, len(values_list), batch_size):
                batch_values = values_list[i:i + batch_size]
                batch_sql = f"""
                INSERT INTO PURCHASE_INVOICE.PUBLIC.INVOICES
                (INVOICE_ID, SUPPLIER_NAME, INVOICE_AMOUNT, PURCHASER_EMAIL, INVOICE_DATE)
                VALUES
                {','.join(batch_values)};
                """
                await execute_sql(server, batch_sql, f"Batch inserting invoices {i+1}-{min(i+batch_size, len(values_list))}", "write")
            
            # 批量插入付款记录 - 使用单次批量插入优化性能
            print(f"💳 批量插入 {len(invoices_data)} 条付款数据...")

            # 构建批量INSERT语句
            payment_values_list = []
            for invoice in invoices_data:
                payment_values_list.append(f"('{invoice['invoice_number']}', {invoice['paid_amount']:.2f}, {invoice['outstanding_flag']})")

            # 批量INSERT - 减少网络往返
            for i in range(0, len(payment_values_list), batch_size):
                batch_values = payment_values_list[i:i + batch_size]
                batch_sql = f"""
                INSERT INTO PURCHASE_INVOICE.PUBLIC.INVOICE_PAYMENTS
                (INVOICE_ID, PAYMENT_AMOUNT, OUTSTANDING_FLAG)
                VALUES
                {','.join(batch_values)};
                """
                await execute_sql(server, batch_sql, f"Batch inserting payments {i+1}-{min(i+batch_size, len(payment_values_list))}", "write")
            
            # 5. 验证设置
            print("\n📋 Step 5: Verifying setup...")
            
            verification_queries = [
                ("SELECT COUNT(*) AS TOTAL_INVOICES FROM PURCHASE_INVOICE.PUBLIC.INVOICES;", "Counting total invoices"),
                ("SELECT COUNT(*) AS TOTAL_PAYMENTS FROM PURCHASE_INVOICE.PUBLIC.INVOICE_PAYMENTS;", "Counting total payments")
            ]
            
            for sql, desc in verification_queries:
                await execute_sql(server, sql, desc, "read")
            
            print("\n🎉 DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("✅ Tables created: INVOICES, INVOICE_PAYMENTS")
            print("✅ Interference data inserted (1000 records)")
            print("\n准备让agent从PDF中读取原始数据并插入数据库...")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Initialize Snowflake database for invoice processing")
    parser.add_argument("--dry-run", action="store_true", help="Show table structure only without executing")
    parser.add_argument("--export", action="store_true", help="Export database content to separate JSONL files in groundtruth_workspace/")
    parser.add_argument("--init-only", action="store_true", help="Initialize database with interference data (1000 interference records only)")
    args = parser.parse_args()

    # 设置随机种子保证再现性
    generate_test_invoices.random.seed(42)

    if args.export:
        print("📤 EXPORTING DATABASE TO JSONL")
        print("=" * 60)
        success = asyncio.run(export_database_to_jsonl())
        if success:
            print("\n✅ Database export completed successfully!")
        else:
            print("\n❌ Database export failed!")
        exit(0 if success else 1)
    elif args.dry_run:
        print("🏦 SNOWFLAKE DATABASE INITIALIZATION (DRY RUN)")
        print("=" * 60)
        display_table_structure()
        print("\n✅ Dry run completed - use without --dry-run to execute")
    else:
        # 运行异步初始化
        asyncio.run(initialize_database())


if __name__ == "__main__":
    main()