# Jifa 文件清理方案总结

## 需求

用户需要定期清理超过 7 天未使用的 heap dump 文件，防止磁盘空间无限增长。

## 解决方案

### 关键发现

1. ✅ Jifa 提供文件列表 API，返回文件创建时间 (`createdTime`)
2. ✅ Jifa 提供文件删除 API (`DELETE /files/{id}`)
3. ❌ Jifa **没有**记录文件的"最后访问时间"，只有创建时间
4. ✅ Jifa 内置自动清理机制（磁盘空间 < 5% 时触发）

### 实现方式

基于**文件创建时间**（而非最后使用时间）进行清理。

---

## 提供的脚本

### 1. 脚本位置

```
/opt/jifa/scripts/cleanup-old-files.sh
```

### 2. 功能特性

- ✅ 根据文件创建时间删除过期文件
- ✅ 支持自定义保留天数（默认 7 天）
- ✅ 分页查询所有文件，避免内存溢出
- ✅ 实时显示清理进度
- ✅ 统计信息输出（总数、删除数、保留数、失败数）
- ✅ Dry-run 模式，测试不实际删除
- ✅ 彩色日志输出，易于阅读
- ✅ 错误处理和依赖检查

### 3. 使用方法

```bash
# 删除超过 7 天的文件
bash /opt/jifa/scripts/cleanup-old-files.sh 7

# 删除超过 30 天的文件
bash /opt/jifa/scripts/cleanup-old-files.sh 30

# Dry-run 测试（不实际删除）
DRY_RUN=true bash /opt/jifa/scripts/cleanup-old-files.sh 7

# 自定义 Jifa 地址
JIFA_HOST=21.6.180.85 JIFA_PORT=8080 bash /opt/jifa/scripts/cleanup-old-files.sh 7
```

---

## Cron 定时任务配置

### 1. 编辑 crontab

```bash
crontab -e
```

### 2. 添加定时任务

```cron
# 每天凌晨 2 点删除超过 7 天的文件
0 2 * * * bash /opt/jifa/scripts/cleanup-old-files.sh 7 >> /var/log/jifa-cleanup.log 2>&1
```

### 3. 其他配置示例

```cron
# 每天凌晨 2 点删除超过 14 天的文件
0 2 * * * bash /opt/jifa/scripts/cleanup-old-files.sh 14 >> /var/log/jifa-cleanup.log 2>&1

# 每周日凌晨 3 点删除超过 30 天的文件
0 3 * * 0 bash /opt/jifa/scripts/cleanup-old-files.sh 30 >> /var/log/jifa-cleanup.log 2>&1

# 每 6 小时删除超过 3 天的文件（高频场景）
0 */6 * * * bash /opt/jifa/scripts/cleanup-old-files.sh 3 >> /var/log/jifa-cleanup.log 2>&1
```

### 4. 验证定时任务

```bash
# 查看已配置的定时任务
crontab -l

# 查看执行日志
tail -f /var/log/jifa-cleanup.log
```

---

## 工作原理

### 1. API 调用流程

```
1. GET /files?type=HEAP_DUMP&page=1&pageSize=100
   → 获取文件列表（分页）
   → 返回: id, uniqueName, originalName, createdTime, size

2. 对每个文件：
   - 解析 createdTime (ISO 8601 格式)
   - 计算文件年龄（当前时间 - 创建时间）
   - 如果年龄 > 保留天数：
     → DELETE /files/{id}

3. 输出统计信息
```

### 2. 时间计算

```bash
# 将 ISO 8601 时间转换为 Unix 时间戳
created_timestamp=$(date -d "2026-01-27T10:30:45" +%s)
current_timestamp=$(date +%s)

# 计算年龄（天数）
age_seconds=$((current_timestamp - created_timestamp))
age_days=$((age_seconds / 86400))

# 判断是否过期
if [ "$age_days" -gt "$retention_days" ]; then
    # 删除文件
fi
```

---

## 脚本输出示例

```
[INFO] ==========================================
[INFO] Jifa 文件自动清理脚本
[INFO] ==========================================
[INFO] 保留天数: 7 天
[INFO] 删除超过 7 天的文件
[INFO] ==========================================

[SUCCESS] Jifa 服务连接正常
[INFO] 查询第 1 页文件（每页 100 条）...
[INFO] 文件过期: ID=1, 年龄=10天, 名称=dump-2026-01-20.hprof
[SUCCESS] 已删除: ID=1, 名称=dump-2026-01-20.hprof, 创建时间=2026-01-20T10:30:45
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

## 重要说明

### 1. 时间字段限制

⚠️ **Jifa 只记录文件创建时间 (createdTime)，没有最后访问时间 (lastAccessTime)**

- ✅ 可以根据创建时间删除文件
- ❌ 无法根据"最后使用时间"删除文件

**影响**:
- 如果文件创建后被频繁访问，仍然会被删除
- 无法区分"活跃使用"和"从未使用"的文件

**解决方案**:
- 如果需要按最后使用时间清理，需要修改 Jifa 源码，添加 `lastAccessTime` 字段
- 或者根据业务需求调整保留天数（例如：高频使用场景保留 3 天，低频场景保留 30 天）

### 2. 内置自动清理

Jifa 已内置自动清理机制：

- **触发条件**: 磁盘空间 < 5%
- **清理策略**: 删除最旧的文件（按创建时间排序）
- **执行频率**: 每分钟检查一次
- **代码位置**: `StorageRelatedTasks.cleanup()` (server/src/main/java/org/eclipse/jifa/server/task/StorageRelatedTasks.java:58-69)

**优点**:
- ✅ 防止磁盘被填满
- ✅ 无需配置

**缺点**:
- ❌ 只在空间不足时触发，无法主动清理
- ❌ 无法自定义保留策略

**建议**:
- 使用 cron 定时任务 + cleanup-old-files.sh 脚本进行主动清理
- 内置清理作为兜底机制

---

## 监控建议

### 1. 查看清理日志

```bash
tail -f /var/log/jifa-cleanup.log
```

### 2. 检查磁盘空间

```bash
df -h /data/jifa
```

### 3. 查看文件数量

```bash
curl -s -G 'http://localhost:8080/jifa-api/files' \
  --data-urlencode 'type=HEAP_DUMP' \
  --data-urlencode 'page=1' \
  --data-urlencode 'pageSize=1' \
  | jq -r '.totalSize'
```

### 4. 查看最旧文件的年龄

```bash
curl -s -G 'http://localhost:8080/jifa-api/files' \
  --data-urlencode 'type=HEAP_DUMP' \
  --data-urlencode 'page=1' \
  --data-urlencode 'pageSize=1' \
  | jq -r '.data[0].createdTime'
```

---

## 推荐配置

根据磁盘大小和使用频率选择合适的保留天数：

| 磁盘大小 | 使用频率 | 推荐保留天数 | Cron 表达式 |
|---------|---------|-------------|------------|
| < 500GB | 高频 | 3 天 | `0 */6 * * *` (每 6 小时) |
| < 500GB | 低频 | 7 天 | `0 2 * * *` (每天凌晨 2 点) |
| 500GB-2TB | 高频 | 7 天 | `0 2 * * *` (每天凌晨 2 点) |
| 500GB-2TB | 低频 | 14 天 | `0 2 * * *` (每天凌晨 2 点) |
| > 2TB | 高频 | 14 天 | `0 2 * * *` (每天凌晨 2 点) |
| > 2TB | 低频 | 30 天 | `0 3 * * 0` (每周日凌晨 3 点) |

---

## 文档位置

- **清理脚本**: `/opt/jifa/scripts/cleanup-old-files.sh`
- **详细指南**: `/opt/jifa/deployment/CLEANUP_GUIDE.md`
- **API 参考**: `/opt/jifa/deployment/API_REFERENCE.md`
- **文档索引**: `/opt/jifa/deployment/INDEX.md`

---

## 相关 API

### 1. 查询文件列表

```bash
curl -G 'http://localhost:8080/jifa-api/files' \
  --data-urlencode 'type=HEAP_DUMP' \
  --data-urlencode 'page=1' \
  --data-urlencode 'pageSize=100' \
  | jq .
```

**响应**:
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

### 2. 删除文件

```bash
curl -X DELETE "http://localhost:8080/jifa-api/files/{file-id}"
```

**响应**: HTTP 200/204（成功）

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

### 问题 4: cron 任务未执行

检查 cron 服务：
```bash
sudo systemctl status crond
sudo systemctl enable crond
sudo systemctl start crond
```

查看 cron 日志：
```bash
sudo tail -f /var/log/cron
```

---

## 下一步

1. **测试脚本**（Dry-run 模式）:
   ```bash
   DRY_RUN=true bash /opt/jifa/scripts/cleanup-old-files.sh 7
   ```

2. **配置定时任务**:
   ```bash
   crontab -e
   # 添加: 0 2 * * * bash /opt/jifa/scripts/cleanup-old-files.sh 7 >> /var/log/jifa-cleanup.log 2>&1
   ```

3. **监控日志**:
   ```bash
   tail -f /var/log/jifa-cleanup.log
   ```

4. **定期检查磁盘空间**:
   ```bash
   df -h /data/jifa
   ```

---

**版本**: 1.0
**更新时间**: 2026-02-03
**作者**: Claude Code Internal
