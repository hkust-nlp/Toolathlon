#!/usr/bin/env python3
"""
Comprehensive test to validate the complete WooCommerce new customer welcome task setup
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add paths for imports
current_dir = Path(__file__).parent
task_dir = current_dir.parent
eval_dir = task_dir / "evaluation"
sys.path.insert(0, str(eval_dir))
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(task_dir))

from customer_database_bigquery import CustomerDatabase

def test_complete_setup():
    """Test the complete setup after database import"""
    print("🧪 COMPREHENSIVE SETUP VALIDATION")
    print("=" * 60)
    
    # Test 1: BigQuery Database Connection
    print("\n1️⃣ Testing BigQuery Database Connection...")
    try:
        db = CustomerDatabase()
        stats = db.get_statistics()
        print(f"   ✅ BigQuery连接成功")
        print(f"   📊 数据库统计: {stats}")
        
        if stats['total_customers'] == 4:
            print(f"   ✅ 客户数量正确: {stats['total_customers']}")
        else:
            print(f"   ❌ 客户数量错误: 期望4，实际{stats['total_customers']}")
            return False
            
    except Exception as e:
        print(f"   ❌ BigQuery连接失败: {e}")
        return False
    
    # Test 2: Customer Data Integrity
    print("\n2️⃣ Testing Customer Data Integrity...")
    expected_customers = [
        "new.customer1@example.com",
        "new.customer2@example.com", 
        "new.customer3@example.com",
        "new.customer4@example.com"
    ]
    
    found_customers = 0
    for email in expected_customers:
        customer = db.get_customer_by_email(email)
        if customer:
            found_customers += 1
            print(f"   ✅ 找到客户: {email} (WooCommerce ID: {customer.get('woocommerce_id')})")
            
            # Check data completeness
            required_fields = ['woocommerce_id', 'email', 'first_name', 'last_name', 'date_created', 'first_order_date']
            missing_fields = [field for field in required_fields if not customer.get(field)]
            if missing_fields:
                print(f"      ⚠️  缺失字段: {missing_fields}")
        else:
            print(f"   ❌ 未找到客户: {email}")
    
    if found_customers == 4:
        print(f"   ✅ 所有测试客户都已正确导入")
    else:
        print(f"   ❌ 客户导入不完整: {found_customers}/4")
        return False
    
    # Test 3: Time Window Logic Issue Analysis
    print("\n3️⃣ Analyzing Time Window Logic...")
    
    # Get a sample customer to check dates
    sample_customer = db.get_customer_by_email("new.customer1@example.com")
    if sample_customer:
        first_order_date = sample_customer.get('first_order_date')
        print(f"   📅 样本客户首单日期: {first_order_date}")
        
        # Parse the date
        try:
            if first_order_date:
                order_date = datetime.fromisoformat(first_order_date.replace('Z', '+00:00'))
                current_date = datetime.now()
                days_diff = (current_date - order_date).days
                
                print(f"   📅 当前日期: {current_date.date()}")
                print(f"   📅 订单日期: {order_date.date()}")
                print(f"   📊 天数差: {days_diff} 天")
                
                if days_diff > 7:
                    print(f"   ⚠️  时间窗口问题: 测试数据超出7天窗口")
                    print(f"   💡 建议: evaluation需要使用固定基准日期或扩大时间窗口")
                else:
                    print(f"   ✅ 时间窗口正常")
                    
        except Exception as e:
            print(f"   ❌ 时间解析失败: {e}")
    
    # Test 4: Evaluation Logic Compatibility
    print("\n4️⃣ Testing Evaluation Logic Compatibility...")
    
    # Test the new customer detection logic (7 days)
    new_customers = db.get_new_customers(7)
    print(f"   📊 7天内新客户: {len(new_customers)}")
    
    if len(new_customers) == 0:
        print(f"   ⚠️  评估可能检测不到客户 (时间窗口问题)")
        
        # Test with larger window
        new_customers_30 = db.get_new_customers(30)
        print(f"   📊 30天内新客户: {len(new_customers_30)}")
        
        if len(new_customers_30) > 0:
            print(f"   💡 建议: 使用30天窗口或固定基准日期")
        else:
            # Test with very large window
            new_customers_365 = db.get_new_customers(365)
            print(f"   📊 365天内新客户: {len(new_customers_365)}")
    else:
        print(f"   ✅ 时间窗口逻辑正常")
    
    # Test 5: Email Status
    print("\n5️⃣ Testing Email Status Logic...")
    customers_needing_email = db.get_customers_without_welcome_email()
    print(f"   📧 需要发送欢迎邮件的客户: {len(customers_needing_email)}")
    
    if len(customers_needing_email) == 4:
        print(f"   ✅ 所有客户都标记为需要欢迎邮件")
    else:
        print(f"   ⚠️  邮件状态可能有问题")
    
    print("\n" + "=" * 60)
    print("📋 SETUP VALIDATION SUMMARY")
    print("=" * 60)
    
    issues = []
    recommendations = []
    
    if stats['new_customers_7_days'] == 0 and stats['total_customers'] > 0:
        issues.append("🔴 时间窗口逻辑问题: 无法检测到7天内的新客户")
        recommendations.append("💡 修复建议: 在evaluation中使用固定基准日期 (2025-09-02)")
    
    if found_customers == 4:
        print("✅ 数据导入: 完全成功")
    else:
        issues.append("🔴 数据导入不完整")
        
    if len(customers_needing_email) == 4:
        print("✅ 邮件状态: 正确配置")
    else:
        issues.append("🔴 邮件状态配置问题")
        
    print("✅ BigQuery连接: 正常工作")
    
    if issues:
        print("\n🔧 发现的问题:")
        for issue in issues:
            print(f"   {issue}")
            
        print("\n💡 修复建议:")
        for rec in recommendations:
            print(f"   {rec}")
            
        return False
    else:
        print("\n🎉 所有测试通过！系统已准备就绪。")
        return True

def create_evaluation_fix_suggestion():
    """Create a suggestion for fixing the evaluation time window"""
    print("\n" + "=" * 60)
    print("🔧 EVALUATION修复建议")
    print("=" * 60)
    
    print("问题: evaluation使用动态时间窗口，无法检测到静态测试数据")
    print()
    print("解决方案选项:")
    print("1. 修改evaluation使用固定基准日期 (推荐)")
    print("2. 扩大时间窗口到30天或更长")  
    print("3. 更新测试数据为当前日期")
    print()
    print("推荐修复代码:")
    print("""
# 在WooCommerceValidator.get_recent_customers()中:
# 替换:
cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

# 为:
# 使用固定基准日期以匹配测试数据
base_date = datetime(2025, 9, 9)  # 测试数据后7天
cutoff_date = (base_date - timedelta(days=days)).isoformat()
""")

if __name__ == "__main__":
    print("🚀 开始完整设置验证...")
    
    success = test_complete_setup()
    create_evaluation_fix_suggestion()
    
    if success:
        print(f"\n✅ 验证成功！任务已准备就绪。")
        sys.exit(0)
    else:
        print(f"\n⚠️  验证发现问题，但数据已成功导入。")
        print(f"主要问题是时间窗口逻辑，可通过修复evaluation解决。")
        sys.exit(1)