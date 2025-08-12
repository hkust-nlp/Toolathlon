# Google Drive API 权限配置指南

## 概述

本文档详细讲解如何配置和限制Google Drive API的权限，以确保系统安全性和功能需求的平衡。

## 当前权限配置

### 现有配置
```python
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',  # Google Sheets完整访问权限
    'https://www.googleapis.com/auth/drive'          # Google Drive完整访问权限
]
```

### 权限说明
- `spreadsheets`: 完整的Google Sheets读写权限
- `drive`: 完整的Google Drive访问权限（**最宽泛的权限**）

## Google Drive API权限层级

### 权限范围层级图
```
Google Drive API 权限层级:

📁 drive (最高权限)
├── 可访问用户所有Drive文件
├── 可创建、读取、修改、删除任何文件
└── 可管理文件夹和共享设置

📂 drive.file (应用文件权限)
├── 只能访问通过此应用创建或打开的文件
├── 无法访问其他应用创建的文件
└── 安全性较高，推荐使用

📖 drive.readonly (只读权限)
├── 可读取用户所有Drive文件
├── 无法修改或删除任何文件
└── 适用于只需要读取的场景

📊 drive.metadata (元数据权限)
├── 可读取文件元数据（名称、大小、创建时间等）
├── 无法访问文件内容
└── 适用于文件管理和搜索

🔍 drive.metadata.readonly (只读元数据)
├── 只能读取文件元数据
├── 无法修改元数据
└── 最小权限，适用于文件列表展示
```

## 详细权限对照表

| 权限范围 | 读取文件 | 创建文件 | 修改文件 | 删除文件 | 访问范围 | 安全级别 |
|---------|---------|---------|---------|---------|---------|----------|
| `drive` | ✅ | ✅ | ✅ | ✅ | 所有文件 | ⚠️ 低 |
| `drive.file` | ✅ | ✅ | ✅ | ✅ | 应用文件 | ✅ 中 |
| `drive.readonly` | ✅ | ❌ | ❌ | ❌ | 所有文件 | ✅ 中 |
| `drive.metadata` | 仅元数据 | ❌ | 仅元数据 | ❌ | 所有文件 | ✅ 高 |
| `drive.metadata.readonly` | 仅元数据 | ❌ | ❌ | ❌ | 所有文件 | ✅ 最高 |

## Google Sheets权限

| 权限范围 | 读取 | 创建 | 修改 | 删除 | 格式化 | 安全级别 |
|---------|------|------|------|------|--------|----------|
| `spreadsheets` | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ 低 |
| `spreadsheets.readonly` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ 高 |

## 权限配置建议

### 1. 按功能分离权限

#### 预处理脚本（需要删除权限）
```python
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',     # Sheets完整访问
    'https://www.googleapis.com/auth/drive.file'        # 只能操作应用创建的文件
]
```

#### Evaluation脚本（只需读取）
```python
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',  # Sheets只读
    'https://www.googleapis.com/auth/drive.readonly'          # Drive只读
]
```

#### 元数据检查脚本（最小权限）
```python
SCOPES = [
    'https://www.googleapis.com/auth/drive.metadata.readonly'  # 只读文件元数据
]
```

### 2. 环境分离

#### 开发环境（较宽权限）
```python
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'  # 开发时使用完整权限
]
```

#### 生产环境（严格权限）
```python
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.file'  # 生产环境限制权限
]
```

## 实际权限问题分析

### 当前遇到的问题

1. **文件所有权冲突**
   - 服务账号A创建的文件，服务账号B无法删除
   - 即使有`drive`权限也无法删除其他用户的文件

2. **解决方案**
   ```python
   # 方案1: 使用drive.file权限（只能删除自己创建的）
   SCOPES = ['https://www.googleapis.com/auth/drive.file']
   
   # 方案2: 文件命名加时间戳避免冲突
   filename = f"2025_Q2_Market_Data_{int(time.time())}"
   
   # 方案3: 检查文件所有者再决定操作
   def check_file_owner(service, file_id):
       file_metadata = service.files().get(fileId=file_id, fields='owners').execute()
       return file_metadata.get('owners', [])
   ```

## 权限修改步骤

### 1. 修改preprocess脚本权限
```python
# 文件: tasks/finalpool/quantitative-financial-analysis/preprocess/main.py
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',     # 保持Sheets完整访问
    'https://www.googleapis.com/auth/drive.file'        # 限制为应用文件
]
```

### 2. 修改evaluation脚本权限
```python
# 文件: tasks/finalpool/quantitative-financial-analysis/evaluation/check_content.py
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',  # 只读Sheets
    'https://www.googleapis.com/auth/drive.readonly'          # 只读Drive
]
```

### 3. 重新授权
修改权限后需要：
1. 删除现有的token文件
2. 重新运行授权流程
3. 用户重新授权新的权限范围

## 安全最佳实践

### 1. 最小权限原则
- 只申请必需的权限
- 定期审查权限使用情况
- 及时移除不需要的权限

### 2. 权限分离
- 不同功能使用不同的服务账号
- 读写操作分离
- 开发和生产环境分离

### 3. 监控和审计
- 记录所有API调用
- 监控异常权限使用
- 定期审计权限配置

### 4. 错误处理
```python
def safe_delete_file(service, file_id):
    try:
        service.files().delete(fileId=file_id).execute()
        return True, "删除成功"
    except HttpError as e:
        if e.resp.status == 403:
            return False, "权限不足，无法删除文件"
        elif e.resp.status == 404:
            return False, "文件不存在"
        else:
            return False, f"删除失败: {e}"
```

## 总结

1. **当前配置**：使用最宽泛的权限，功能完整但安全性较低
2. **建议配置**：根据功能需求分别配置不同级别的权限
3. **权限问题**：主要由文件所有权引起，需要合理的权限配置和错误处理
4. **最佳实践**：遵循最小权限原则，实现权限分离和监控

通过合理配置权限，可以在保证功能需求的同时最大化系统安全性。