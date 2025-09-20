# 已弃用的WooCommerce客户端实现
#
# 该文件已被替换为使用 utils/app_specific/woocommerce.client 中的通用WooCommerceClient
#
# 新的实现提供了以下优势：
# 1. 更完整的功能：批量删除、完整的订单管理、产品分类管理等
# 2. 更好的错误处理和请求节流
# 3. 支持店铺重置等高级功能
# 4. 一致的API接口
#
# 迁移指南：
# 原代码：from preprocess.woocommerce_client import WooCommerceClient
# 新代码：from utils.app_specific.woocommerce.client import WooCommerceClient
#
# 主要改动：
# - delete_existing_orders() 现在使用批量删除功能
# - 所有基础 CRUD 操作保持兼容
# - 增强的错误处理和日志记录