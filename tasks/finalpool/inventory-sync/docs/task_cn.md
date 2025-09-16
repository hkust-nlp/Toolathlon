我是Woocommerce的店主，我的店铺在以下城市建有仓库：纽约、Boston、Dallas、LA、San Francisco、Houston
请帮我：
1. 检测各仓库SQLite数据库中已上传但线上商店还未更新的最新商品库存清单（以Product ID为标识）
2. 调用WooCommerce的工具按照城市到区域的映射关系同步更新到WooCommerce的线上库存：
   - East区域：纽约、Boston
   - South区域：Dallas、Houston
   - West区域：LA、San Francisco
3. 生成库存同步报告，显示各RegionInventory更新状态
数据库的信息从 `warehouse`目录下获取,使用woocommerce mcp server来与WooCommerce交互获取数据更新，不要自己写API实现！

请按照如下格式保存库存同步报告 `report.yaml`
```yaml
{
  "report_format_specification": {
    "version": "1.0",
    "description": "Server可读的库存同步报告标准格式",
    "required_fields": [
      "report_id",
      "timestamp", 
      "summary",
      "regions",
      "validation_hash"
    ]
  },
  "template": {
    "report_id": "SYNC_YYYYMMDD_HHMMSS",
    "timestamp": "2024-01-01T12:00:00Z",
    "summary": {
      "total_processed": 0,
      "success_count": 0,
      "failed_count": 0,
      "success_rate": 0.0
    },
    "inventory": {
      "total_local_quantity": 0,
      "total_online_quantity": 0,
      "quantity_discrepancies": 0
    },
    "regions": {
      "East": {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "total_local_qty": 0,
        "total_online_qty": 0
      },
      "West": {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "total_local_qty": 0,
        "total_online_qty": 0
      },
      "South": {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "total_local_qty": 0,
        "total_online_qty": 0
      }
    },
    "validation_hash": "md5_hash_of_core_data"
  },
  "validation_rules": {
    "summary.total_processed": "必须等于所有区域processed之和",
    "summary.success_count": "必须等于所有区域success之和",
    "summary.success_rate": "必须等于(success_count/total_processed)*100",
    "inventory.total_local_quantity": "必须等于所有区域total_local_qty之和",
    "validation_hash": "必须匹配core_data的MD5值"
  },
  "example_output": {
    "report_id": "SYNC_20241201_143022",
    "timestamp": "2024-12-01T14:30:22Z",
    "summary": {
      "total_processed": 7,
      "success_count": 6,
      "failed_count": 1,
      "success_rate": 85.71
    },
    "inventory": {
      "total_local_quantity": 775,
      "total_online_quantity": 770,
      "quantity_discrepancies": 6
    },
    "regions": {
      "East": {
        "processed": 3,
        "success": 3,
        "failed": 0,
        "total_local_qty": 320,
        "total_online_qty": 310
      },
      "West": {
        "processed": 2,
        "success": 1,
        "failed": 1,
        "total_local_qty": 275,
        "total_online_qty": 260
      },
      "South": {
        "processed": 2,
        "success": 2,
        "failed": 0,
        "total_local_qty": 180,
        "total_online_qty": 200
      }
    },
    "validation_hash": "a1b2c3d4e5f6g7h8"
  }
}
```