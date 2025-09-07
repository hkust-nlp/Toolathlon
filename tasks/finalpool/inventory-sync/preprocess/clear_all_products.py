#!/usr/bin/env python3
"""
清空WooCommerce商店所有产品的工具
谨慎使用：此操作将删除商店中的所有商品和分类
"""

import requests
from requests.auth import HTTPBasicAuth
import json
import time
import sys
from typing import List, Dict, Any, Tuple
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.append(task_dir)

class WooCommerceCleaner:
    """WooCommerce商店清理工具"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        初始化清理工具
        
        Args:
            site_url: WooCommerce网站URL
            consumer_key: WooCommerce API消费者密钥
            consumer_secret: WooCommerce API消费者密钥
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/v3"
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session = requests.Session()
        self.session.auth = self.auth
        
        # API调用限制
        self.request_delay = 0.2  # 每次请求间隔200ms
        self.batch_size = 100     # 批量操作大小
        
        print(f"🔧 初始化WooCommerce清理工具: {self.site_url}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Tuple[bool, Any]:
        """发送API请求"""
        url = f"{self.api_base}/{endpoint}"
        
        try:
            time.sleep(self.request_delay)
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params)
            else:
                return False, f"不支持的HTTP方法: {method}"
            
            if response.status_code in [200, 201, 204]:
                try:
                    return True, response.json() if response.text else {}
                except:
                    return True, {}
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, str(e)
    
    def test_connection(self) -> bool:
        """测试API连接"""
        print("🔍 测试API连接...")
        
        success, response = self._make_request('GET', 'products', params={'per_page': 1})
        
        if success:
            print("✅ API连接成功")
            return True
        else:
            print(f"❌ API连接失败: {response}")
            return False
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """获取所有商品"""
        print("📦 获取所有商品...")
        
        all_products = []
        page = 1
        
        while True:
            success, products = self._make_request('GET', 'products', params={
                'per_page': self.batch_size,
                'page': page,
                'status': 'any'  # 获取所有状态的商品
            })
            
            if not success:
                print(f"❌ 获取第{page}页商品失败: {products}")
                break
            
            if not products:
                break
            
            all_products.extend(products)
            print(f"  📄 第{page}页: {len(products)} 个商品")
            
            if len(products) < self.batch_size:
                break
            
            page += 1
        
        print(f"📊 总共找到 {len(all_products)} 个商品")
        return all_products
    
    def get_all_categories(self) -> List[Dict[str, Any]]:
        """获取所有商品分类"""
        print("📂 获取所有商品分类...")
        
        all_categories = []
        page = 1
        
        while True:
            success, categories = self._make_request('GET', 'products/categories', params={
                'per_page': self.batch_size,
                'page': page
            })
            
            if not success:
                print(f"❌ 获取第{page}页分类失败: {categories}")
                break
            
            if not categories:
                break
            
            all_categories.extend(categories)
            print(f"  📄 第{page}页: {len(categories)} 个分类")
            
            if len(categories) < self.batch_size:
                break
            
            page += 1
        
        print(f"📊 总共找到 {len(all_categories)} 个分类")
        return all_categories
    
    def delete_products_batch(self, product_ids: List[int]) -> Tuple[int, int]:
        """批量删除商品"""
        success_count = 0
        failed_count = 0
        
        # WooCommerce支持批量删除
        batch_data = {
            'delete': [{'id': pid} for pid in product_ids]
        }
        
        success, response = self._make_request('POST', 'products/batch', data=batch_data)
        
        if success:
            deleted = response.get('delete', [])
            for item in deleted:
                if 'error' in item:
                    failed_count += 1
                    print(f"    ❌ 删除商品 {item.get('id', 'unknown')} 失败: {item['error']['message']}")
                else:
                    success_count += 1
        else:
            print(f"❌ 批量删除失败: {response}")
            failed_count = len(product_ids)
        
        return success_count, failed_count
    
    def delete_all_products(self, confirm: bool = False) -> Tuple[int, int]:
        """删除所有商品"""
        if not confirm:
            print("⚠️ 此操作将删除所有商品，请使用 confirm=True 参数确认")
            return 0, 0
        
        products = self.get_all_products()
        
        if not products:
            print("✅ 没有商品需要删除")
            return 0, 0
        
        print(f"🗑️ 开始删除 {len(products)} 个商品...")
        
        total_success = 0
        total_failed = 0
        
        # 分批删除
        for i in range(0, len(products), self.batch_size):
            batch = products[i:i + self.batch_size]
            batch_ids = [p['id'] for p in batch]
            
            print(f"  🗂️ 删除第 {i//self.batch_size + 1} 批 ({len(batch_ids)} 个商品)...")
            
            success_count, failed_count = self.delete_products_batch(batch_ids)
            total_success += success_count
            total_failed += failed_count
            
            print(f"    ✅ 成功: {success_count}, ❌ 失败: {failed_count}")
        
        print(f"📊 商品删除完成: 成功 {total_success}, 失败 {total_failed}")
        return total_success, total_failed
    
    def delete_categories_batch(self, category_ids: List[int]) -> Tuple[int, int]:
        """批量删除分类"""
        success_count = 0
        failed_count = 0
        
        # WooCommerce支持批量删除分类
        batch_data = {
            'delete': [{'id': cid, 'force': True} for cid in category_ids]  # force=True 永久删除
        }
        
        success, response = self._make_request('POST', 'products/categories/batch', data=batch_data)
        
        if success:
            deleted = response.get('delete', [])
            for item in deleted:
                if 'error' in item:
                    failed_count += 1
                    print(f"    ❌ 删除分类 {item.get('id', 'unknown')} 失败: {item['error']['message']}")
                else:
                    success_count += 1
        else:
            print(f"❌ 批量删除分类失败: {response}")
            failed_count = len(category_ids)
        
        return success_count, failed_count
    
    def delete_all_categories(self, confirm: bool = False) -> Tuple[int, int]:
        """删除所有商品分类（除了默认分类）"""
        if not confirm:
            print("⚠️ 此操作将删除所有分类，请使用 confirm=True 参数确认")
            return 0, 0
        
        categories = self.get_all_categories()
        
        # 过滤掉默认分类（通常ID为15，名称为"Uncategorized"）
        deletable_categories = [cat for cat in categories if cat['id'] != 15 and cat['slug'] != 'uncategorized']
        
        if not deletable_categories:
            print("✅ 没有可删除的分类")
            return 0, 0
        
        print(f"🗑️ 开始删除 {len(deletable_categories)} 个分类...")
        
        total_success = 0
        total_failed = 0
        
        # 分批删除
        for i in range(0, len(deletable_categories), self.batch_size):
            batch = deletable_categories[i:i + self.batch_size]
            batch_ids = [c['id'] for c in batch]
            
            print(f"  🗂️ 删除第 {i//self.batch_size + 1} 批 ({len(batch_ids)} 个分类)...")
            
            success_count, failed_count = self.delete_categories_batch(batch_ids)
            total_success += success_count
            total_failed += failed_count
            
            print(f"    ✅ 成功: {success_count}, ❌ 失败: {failed_count}")
        
        print(f"📊 分类删除完成: 成功 {total_success}, 失败 {total_failed}")
        return total_success, total_failed
    
    def clear_all_store_data(self, confirm: bool = False) -> Dict[str, Tuple[int, int]]:
        """清空商店所有数据（商品和分类）"""
        if not confirm:
            print("⚠️ 此操作将清空整个商店，请使用 confirm=True 参数确认")
            return {"products": (0, 0), "categories": (0, 0)}
        
        print("🧹 开始清空WooCommerce商店...")
        print("=" * 60)
        
        results = {}
        
        # 1. 删除所有商品
        print("\n1️⃣ 删除所有商品")
        results["products"] = self.delete_all_products(confirm=True)
        
        # 2. 删除所有分类
        print("\n2️⃣ 删除所有分类")
        results["categories"] = self.delete_all_categories(confirm=True)
        
        print("\n" + "=" * 60)
        print("🎉 商店清理完成!")
        
        total_products = sum(results["products"])
        total_categories = sum(results["categories"])
        
        print(f"📊 清理摘要:")
        print(f"  商品: 成功删除 {results['products'][0]}, 失败 {results['products'][1]}")
        print(f"  分类: 成功删除 {results['categories'][0]}, 失败 {results['categories'][1]}")
        print(f"  总计: {total_products + total_categories} 个项目")
        
        return results
    
    def get_store_summary(self) -> Dict[str, Any]:
        """获取商店摘要信息"""
        print("📊 获取商店摘要...")
        
        # 获取商品统计
        success, products = self._make_request('GET', 'products', params={'per_page': 1})
        total_products = 0
        if success:
            # 从响应头获取总数
            try:
                # 简单方式：获取所有商品并计数（对于大量商品可能较慢）
                all_products = self.get_all_products()
                total_products = len(all_products)
            except:
                total_products = 0
        
        # 获取分类统计
        success, categories = self._make_request('GET', 'products/categories', params={'per_page': 1})
        total_categories = 0
        if success:
            try:
                all_categories = self.get_all_categories()
                total_categories = len(all_categories)
            except:
                total_categories = 0
        
        summary = {
            "total_products": total_products,
            "total_categories": total_categories,
            "store_url": self.site_url
        }
        
        print(f"  商品总数: {total_products}")
        print(f"  分类总数: {total_categories}")
        
        return summary

def load_config_from_file() -> Dict[str, str]:
    """从配置文件加载WooCommerce凭据"""
    try:
        from token_key_session import all_token_key_session

        return {
            "site_url": all_token_key_session.woocommerce_site_url.rstrip('/'),
            "consumer_key": all_token_key_session.woocommerce_api_key,
            "consumer_secret": all_token_key_session.woocommerce_api_secret
        }
    except:
        print(f"❌ 配置文件不存在: {config_file}")
        return {}

def main():
    """主函数"""
    print("🧹 WooCommerce商店清理工具")
    print("=" * 50)
    
    # 尝试从配置文件加载
    config = load_config_from_file()
    
    if config and all(config.values()):
        print("✅ 从配置文件加载凭据")
        site_url = config["site_url"]
        consumer_key = config["consumer_key"]
        consumer_secret = config["consumer_secret"]
    else:
        print("📝 请输入WooCommerce凭据:")
        site_url = input("网站URL: ").strip()
        consumer_key = input("Consumer Key: ").strip()
        consumer_secret = input("Consumer Secret: ").strip()
    
    if not all([site_url, consumer_key, consumer_secret]):
        print("❌ 请提供完整的凭据信息")
        sys.exit(1)
    
    # 创建清理器
    cleaner = WooCommerceCleaner(site_url, consumer_key, consumer_secret)
    
    # 测试连接
    if not cleaner.test_connection():
        print("❌ 无法连接到WooCommerce API")
        sys.exit(1)
    
    # 显示当前商店状态
    print("\n📊 当前商店状态:")
    summary = cleaner.get_store_summary()
    
    if summary["total_products"] == 0 and summary["total_categories"] <= 1:
        print("✅ 商店已经是空的")
        return
    
    # # 确认操作
    # print(f"\n⚠️ 警告：即将删除以下内容:")
    # print(f"  - {summary['total_products']} 个商品")
    # print(f"  - {summary['total_categories']} 个分类")
    # print(f"  - 网站: {summary['store_url']}")
    
    # confirm = input("\n确认清空商店? 输入 'YES' 继续: ").strip()
    
    # if confirm != "YES":
    #     print("❌ 操作已取消")
    #     sys.exit(0)
    
    # 执行清理
    results = cleaner.clear_all_store_data(confirm=True)
    
    # 最终验证
    print("\n🔍 验证清理结果...")
    final_summary = cleaner.get_store_summary()
    
    if final_summary["total_products"] == 0:
        print("✅ 所有商品已清理完成")
    else:
        print(f"⚠️ 仍有 {final_summary['total_products']} 个商品未删除")
    
    if final_summary["total_categories"] <= 1:  # 保留默认分类
        print("✅ 所有自定义分类已清理完成")
    else:
        print(f"⚠️ 仍有 {final_summary['total_categories']} 个分类未删除")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)
