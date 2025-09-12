# 库存预警邮件模板

## 邮件主题
【库存预警】{product_name} 库存低于安全阈值

## 邮件正文

尊敬的{recipient_name}，

系统检测到以下产品库存低于安全阈值，请及时处理：

## 产品信息
- **产品名称**: {product_name}
- **SKU**: {sku} 
- **当前库存**: {current_stock}
- **安全阈值**: {threshold}
- **供应商**: {supplier_name}
- **供应商联系方式**: {supplier_contact}

## 建议操作
建议采购数量：{suggested_quantity}

请点击以下链接查看采购需求清单：
{sheets_link}

---
此邮件由库存监控系统自动发送  
发送时间：{timestamp}