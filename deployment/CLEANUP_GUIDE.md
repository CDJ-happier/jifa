# Jifa 文件自动清理指南

## 概述

Jifa 提供了文件清理功能，可以删除过期的 heap dump 文件，防止磁盘空间无限增长。

## 清理策略

### 1. Jifa 内置自动清理

Jifa 已内置自动清理机制：

- **触发条件**: 当可用磁盘空间 < 5% 时
- **清理策略**: 删除最旧的文件（按创建时间排序）
- **执行频率**: 每分钟检查一次
- **位置**: `StorageRelatedTasks.cleanup()` 方法

**优点**:
- ✅ 自动运行，无需配置
- ✅ 确保磁盘不会被填满

**缺点**:
- ❌ 只在磁盘空间不足时才触发
- ❌ 无法按文件年龄定期清理
- ❌ 无法自定义保留策略

### 2. 定时清理脚本（推荐）

为了更好地控制文件保留策略，可以使用定时清理脚本。

---

## 清理脚本使用

### 1. 脚本位置

```bash
/opt/jifa/scripts/cleanup-old-files.sh
```

### 2. 基本使用

```bash
# 删除超过 7 天的文件（默认）
bash /opt/jifa/scripts/cleanup-old-files.sh 7

# 删除超过 30 天的文件
bash /opt/jifa/scripts/cleanup-old-files.sh 30

# 删除超过 1 天的文件
bash /opt/jifa/scripts/cleanup-old-files.sh 1
```

### 3. 环境变量

```bash
# 自定义 Jifa 服务地址
export JIFA_HOST="21.6.180.85"
export JIFA_PORT="8080"

bash /opt/jifa/scripts/cleanup-old-files.sh 7
```

### 4. Dry-Run 模式

测试脚本，不实际删除文件：

```bash
DRY_RUN=true bash /opt/jifa/scripts/cleanup-old-files.sh 7
```

输出示例：
```
[INFO] ==========================================
[INFO] Jifa 文件自动清理脚本
[INFO] ==========================================
[INFO] 保留天数: 7 天
[INFO] 删除超过 7 天的文件
[WARN] DRY-RUN 模式：不会实际删除文件
[INFO] ==========================================

[SUCCESS] Jifa 服务连接正常
[INFO] 查询第 1 页文件（每页 100 条）...
[INFO] 文件过期: ID=1, 年龄=10天, 名称=dump-2026-01-20.hprof
[WARN] [DRY-RUN] 将删除: ID=1, 名称=dump-2026-01-20.hprof, 创建时间=2026-01-20T10:30:45
[INFO] 文件保留: ID=2, 年龄=3天, 名称=dump-2026-01-30.hprof

[INFO] ==========================================
[INFO] 清理完成
[INFO] ==========================================
[INFO] 总文件数: 2
[SUCCESS] 已删除: 1
[INFO] 已保留: 1
[INFO] ==========================================
```

---

## 配置 Cron 定时任务

### 1. 编辑 crontab

```bash
crontab -e
```

### 2. 添加定时任务

```cron
# 每天凌晨 2 点执行，删除超过 7 天的文件
0 2 * * * bash /opt/jifa/scripts/cleanup-old-files.sh 7 >> /var/log/jifa-cleanup.log 2>&1

# 每周日凌晨 3 点执行，删除超过 30 天的文件
0 3 * * 0 bash /opt/jifa/scripts/cleanup-old-files.sh 30 >> /var/log/jifa-cleanup.log 2>&1
```

### 3. 验证定时任务

```bash
# 查看已配置的定时任务
crontab -l

# 查看执行日志
tail -f /var/log/jifa-cleanup.log
```

---

## Cron 时间表达式说明

格式: `分钟 小时 日 月 星期 命令`

| 字段 | 允许值 | 特殊字符 |
|-----|-------|----------|
| 分钟 | 0-59 | * , - / |
| 小时 | 0-23 | * , - / |
| 日 | 1-31 | * , - / |
| 月 | 1-12 | * , - / |
| 星期 | 0-7 (0或7表示周日) | * , - / |

**示例**:

```cron
# 每天凌晨 2 点
0 2 * * *

# 每周一凌晨 3 点
0 3 * * 1

# 每月 1 号凌晨 4 点
0 4 1 * *

# 每 6 小时执行一次
0 */6 * * *

# 每周日凌晨 2:30
30 2 * * 0
```

---

## 工作原理

### 1. 脚本流程

```
1. 检查依赖 (curl, jq, date)
   ↓
2. 检查 Jifa 服务连接
   ↓
3. 分页获取所有 HEAP_DUMP 文件
   ↓
4. 对每个文件：
   - 解析创建时间 (createdTime)
   - 计算文件年龄（天数）
   - 如果年龄 > 保留天数：
     → 调用 DELETE /files/{id} 删除
   - 否则保留
   ↓
5. 输出统计信息
```

### 2. API 调用

**获取文件列表**:
```bash
GET /jifa-api/files?type=HEAP_DUMP&page=1&pageSize=100
```

响应示例:
```json
{
  "data": [
    {
      "id": 1,
      "uniqueName": "497dda82-542e-416c-8d5c-352eb252dbbe",
      "originalName": "dump.hprof",
      "type": "HEAP_DUMP",
      "size": 393046228,
      "createdTime": "2026-01-27T10:30:45"
    }
  ],
  "totalSize": 1,
  "totalPage": 1
}
```

**删除文件**:
```bash
DELETE /jifa-api/files/{file-id}
```

响应: HTTP 200/204（成功）

---

## 时间计算说明

### 1. 时间字段

- **createdTime**: 文件创建时间（ISO 8601 格式）
- **格式**: `2026-01-27T10:30:45` 或 `2026-01-27T10:30:45.123`

### 2. 年龄计算

```bash
# 当前时间戳
current_timestamp=$(date +%s)

# 文件创建时间戳
created_timestamp=$(date -d "${createdTime}" +%s)

# 年龄（秒）
age_seconds=$((current_timestamp - created_timestamp))

# 年龄（天）
age_days=$((age_seconds / 86400))

# 判断是否过期
if [ "$age_days" -gt "$retention_days" ]; then
    # 删除文件
fi
```

---

## 重要说明

### 1. 时间字段限制

⚠️ **Jifa 只记录文件创建时间 (createdTime)，没有最后访问时间 (lastAccessTime)**

- ✅ 可以根据创建时间删除文件
- ❌ 无法根据"最后使用时间"删除文件

如果需要按使用时间清理，需要修改 Jifa 源码添加 `lastAccessTime` 字段。

### 2. 删除影响

- 删除文件后，Web UI 中对应的分析结果将不可访问
- 物理文件会从 `/data/jifa/storage/heap-dump/` 目录中删除
- 删除记录会保存到 `deleted_file` 表中（用于审计）

### 3. 安全建议

- ✅ 先使用 `DRY_RUN=true` 测试
- ✅ 定期备份重要的 heap dump 文件
- ✅ 设置合理的保留天数（建议 7-30 天）
- ✅ 监控磁盘空间使用情况

---

## 监控和告警

### 1. 查看清理日志

```bash
tail -f /var/log/jifa-cleanup.log
```

### 2. 检查磁盘空间

```bash
df -h /data/jifa
```

### 3. 查看 Jifa 文件数量

```bash
curl -s -G 'http://localhost:8080/jifa-api/files' \
  --data-urlencode 'type=HEAP_DUMP' \
  --data-urlencode 'page=1' \
  --data-urlencode 'pageSize=1' \
  | jq -r '.totalSize'
```

### 4. 集成到监控系统

可以将脚本输出解析后发送到监控系统：

```bash
#!/bin/bash
# 执行清理并提取统计信息
output=$(bash /opt/jifa/scripts/cleanup-old-files.sh 7 2>&1)

deleted_count=$(echo "$output" | grep "已删除:" | awk '{print $2}')
kept_count=$(echo "$output" | grep "已保留:" | awk '{print $2}')

# 发送到 Prometheus/Grafana/其他监控系统
echo "jifa_cleanup_deleted_count $deleted_count"
echo "jifa_cleanup_kept_count $kept_count"
```

---

## 故障排查

### 问题 1: jq 命令未找到

```bash
sudo yum install -y jq
```

### 问题 2: 脚本权限不足

```bash
chmod +x /opt/jifa/scripts/cleanup-old-files.sh
```

### 问题 3: 无法连接到 Jifa 服务

检查服务状态：
```bash
sudo systemctl status jifa
```

检查端口监听：
```bash
sudo netstat -tlnp | grep 8080
```

### 问题 4: 时间解析失败

确保系统 `date` 命令支持 `-d` 参数：
```bash
date -d "2026-01-27T10:30:45" +%s
```

如果失败，可能需要安装 GNU coreutils。

### 问题 5: cron 任务未执行

检查 cron 服务：
```bash
sudo systemctl status crond
sudo systemctl start crond
sudo systemctl enable crond
```

检查 cron 日志：
```bash
sudo tail -f /var/log/cron
```

---

## 推荐配置

### 1. 小型部署（单节点，磁盘 < 500GB）

```cron
# 每天凌晨 2 点删除超过 7 天的文件
0 2 * * * bash /opt/jifa/scripts/cleanup-old-files.sh 7 >> /var/log/jifa-cleanup.log 2>&1
```

### 2. 中型部署（磁盘 500GB - 2TB）

```cron
# 每天凌晨 2 点删除超过 14 天的文件
0 2 * * * bash /opt/jifa/scripts/cleanup-old-files.sh 14 >> /var/log/jifa-cleanup.log 2>&1
```

### 3. 大型部署（磁盘 > 2TB）

```cron
# 每天凌晨 2 点删除超过 30 天的文件
0 2 * * * bash /opt/jifa/scripts/cleanup-old-files.sh 30 >> /var/log/jifa-cleanup.log 2>&1
```

### 4. 高频使用场景

```cron
# 每 6 小时删除超过 3 天的文件
0 */6 * * * bash /opt/jifa/scripts/cleanup-old-files.sh 3 >> /var/log/jifa-cleanup.log 2>&1
```

---

## API 参考

### 1. 查询文件列表

```bash
curl -G 'http://localhost:8080/jifa-api/files' \
  --data-urlencode 'type=HEAP_DUMP' \
  --data-urlencode 'page=1' \
  --data-urlencode 'pageSize=100' \
  | jq .
```

### 2. 删除文件

```bash
curl -X DELETE "http://localhost:8080/jifa-api/files/{file-id}"
```

### 3. 查询单个文件

```bash
curl "http://localhost:8080/jifa-api/files/{id-or-unique-name}" | jq .
```

---

## 相关文档

- [API 参考](API_REFERENCE.md)
- [自动化指南](QUICKSTART_AUTOMATION.md)
- [部署文档](DEPLOYMENT.md)

---

**版本**: 1.0
**更新时间**: 2026-02-03
