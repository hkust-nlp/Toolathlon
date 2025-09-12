import mysql.connector
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional

class WooCommerceOrderDateUpdater:
    """直接通过数据库更新WooCommerce订单的创建日期"""
    
    def __init__(self, db_config: Dict):
        """
        初始化数据库连接
        
        Args:
            db_config: 数据库配置
            {
                'host': 'localhost',
                'user': 'username', 
                'password': 'password',
                'database': 'database_name'
            }
        """
        self.db_config = db_config
        self.connection = None
        
    def connect(self):
        """连接到数据库"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            print("✅ 数据库连接成功")
            return True
        except mysql.connector.Error as err:
            print(f"❌ 数据库连接失败: {err}")
            return False
    
    def update_order_date(self, order_id: int, historical_date: str) -> bool:
        """
        更新订单的创建日期
        
        Args:
            order_id: WooCommerce订单ID
            historical_date: 历史日期 (ISO格式: "2025-09-01T10:30:00")
        
        Returns:
            是否更新成功
        """
        if not self.connection:
            print("❌ 数据库未连接")
            return False
            
        try:
            cursor = self.connection.cursor()
            
            # 转换日期格式
            dt = datetime.fromisoformat(historical_date.replace('Z', ''))
            mysql_date = dt.strftime('%Y-%m-%d %H:%M:%S')
            mysql_date_gmt = dt.strftime('%Y-%m-%d %H:%M:%S')  # 简化处理，实际应该转换时区
            
            # 更新订单日期
            update_query = """
                UPDATE wp_posts 
                SET post_date = %s,
                    post_date_gmt = %s,
                    post_modified = %s,
                    post_modified_gmt = %s
                WHERE ID = %s AND post_type = 'shop_order'
            """
            
            cursor.execute(update_query, (mysql_date, mysql_date_gmt, mysql_date, mysql_date_gmt, order_id))
            
            if cursor.rowcount > 0:
                self.connection.commit()
                print(f"✅ 订单 #{order_id} 日期已更新为: {historical_date}")
                
                # 添加订单备注
                self._add_order_note(order_id, f"订单创建日期已更新为历史日期: {historical_date}")
                
                return True
            else:
                print(f"⚠️ 未找到订单 #{order_id} 或订单类型不正确")
                return False
                
        except mysql.connector.Error as err:
            print(f"❌ 更新订单日期失败: {err}")
            return False
        finally:
            cursor.close()
    
    def _add_order_note(self, order_id: int, note: str):
        """为订单添加备注"""
        try:
            cursor = self.connection.cursor()
            
            note_data = {
                'comment_post_ID': order_id,
                'comment_author': 'system',
                'comment_content': note,
                'comment_type': 'order_note',
                'comment_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'comment_date_gmt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'comment_approved': 1
            }
            
            insert_query = """
                INSERT INTO wp_comments 
                (comment_post_ID, comment_author, comment_content, comment_type, 
                 comment_date, comment_date_gmt, comment_approved)
                VALUES (%(comment_post_ID)s, %(comment_author)s, %(comment_content)s, 
                        %(comment_type)s, %(comment_date)s, %(comment_date_gmt)s, %(comment_approved)s)
            """
            
            cursor.execute(insert_query, note_data)
            self.connection.commit()
            
        except mysql.connector.Error as err:
            print(f"⚠️ 添加订单备注失败: {err}")
        finally:
            cursor.close()
    
    def batch_update_orders_from_meta(self) -> int:
        """
        从订单元数据批量更新历史日期
        
        Returns:
            更新的订单数量
        """
        if not self.connection:
            print("❌ 数据库未连接")
            return 0
            
        try:
            cursor = self.connection.cursor()
            
            # 查找所有需要更新历史日期的订单
            query = """
                SELECT p.ID, 
                       original_date.meta_value as original_date,
                       simulated.meta_value as is_simulated
                FROM wp_posts p
                LEFT JOIN wp_postmeta original_date ON p.ID = original_date.post_id 
                    AND original_date.meta_key = 'original_date_created'
                LEFT JOIN wp_postmeta simulated ON p.ID = simulated.post_id 
                    AND simulated.meta_key = 'simulated_historical_order'
                WHERE p.post_type = 'shop_order'
                  AND original_date.meta_value IS NOT NULL
                  AND simulated.meta_value = 'true'
            """
            
            cursor.execute(query)
            orders_to_update = cursor.fetchall()
            
            updated_count = 0
            for order_id, original_date, is_simulated in orders_to_update:
                if self.update_order_date(order_id, original_date):
                    updated_count += 1
            
            print(f"📊 批量更新完成，共更新 {updated_count} 个订单")
            return updated_count
            
        except mysql.connector.Error as err:
            print(f"❌ 批量更新失败: {err}")
            return 0
        finally:
            cursor.close()
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("🔒 数据库连接已关闭")


# 使用示例
if __name__ == "__main__":
    # 数据库配置（需要根据实际情况修改）
    db_config = {
        'host': 'localhost',
        'user': 'wordpress_user',
        'password': 'wordpress_password', 
        'database': 'wordpress_db'
    }
    
    updater = WooCommerceOrderDateUpdater(db_config)
    
    if updater.connect():
        # 方式1：单个订单更新
        # updater.update_order_date(198, "2025-09-02T10:30:00")
        
        # 方式2：批量更新所有标记的订单
        updater.batch_update_orders_from_meta()
        
        updater.close() 