# Jifa 文件清理快速参考

## 一键清理命令

```bash
# 删除超过 7 天的文件
bash /opt/jifa/scripts/cleanup-old-files.sh 7

# 测试模式（不实际删除）
DRY_RUN=true bash /opt/jifa/scripts/cleanup-old-files.sh 7
```

## 配置定时任务

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨 2 点执行）
0 2 * * * bash /opt/jifa/scripts/cleanup-old-files.sh 7 >> /var/log/jifa-cleanup.log 2>&1

# 查看已配置的任务
crontab -l

# 查看执行日志
tail -f /var/log/jifa-cleanup.log
```

## Cron 时间表达式

```
格式: 分钟 小时 日 月 星期

示例:
0 2 * * *       # 每天凌晨 2 点
0 */6 * * *     # 每 6 小时
0 3 * * 0       # 每周日凌晨 3 点
0 4 1 * *       # 每月 1 号凌晨 4 点
```

## API 调用示例

```bash
# 查询文件列表
curl -G 'http://localhost:8080/jifa-api/files' \
  --data-urlencode 'type=HEAP_DUMP' \
  --data-urlencode 'page=1' \
  --data-urlencode 'pageSize=100'

# 删除文件
curl -X DELETE "http://localhost:8080/jifa-api/files/{file-id}"

# 查看文件总数
curl -s -G 'http://localhost:8080/jifa-api/files' \
  --data-urlencode 'type=HEAP_DUMP' \
  --data-urlencode 'page=1' \
  --data-urlencode 'pageSize=1' \
  | jq -r '.totalSize'
```

## 推荐配置

| 场景 | 保留天数 | Cron 表达式 |
|-----|---------|------------|
| 小型/高频 | 3 天 | `0 */6 * * *` |
| 小型/低频 | 7 天 | `0 2 * * *` |
| 中型/高频 | 7 天 | `0 2 * * *` |
| 中型/低频 | 14 天 | `0 2 * * *` |
| 大型/高频 | 14 天 | `0 2 * * *` |
| 大型/低频 | 30 天 | `0 3 * * 0` |

## 监控命令

```bash
# 检查磁盘空间
df -h /data/jifa

# 查看清理日志
tail -f /var/log/jifa-cleanup.log

# 查看 Jifa 服务状态
sudo systemctl status jifa

# 查看 cron 服务状态
sudo systemctl status crond

# 查看 cron 日志
sudo tail -f /var/log/cron
```

## 故障排查

```bash
# 安装依赖
sudo yum install -y jq bc

# 赋予执行权限
chmod +x /opt/jifa/scripts/cleanup-old-files.sh

# 启动 cron 服务
sudo systemctl enable crond
sudo systemctl start crond

# 测试脚本
bash /opt/jifa/scripts/cleanup-old-files.sh --help
```

## 重要提醒

⚠️ **Jifa 只记录创建时间，没有最后访问时间**
- 文件按创建时间删除，而非使用时间
- 建议根据业务场景调整保留天数

✅ **Jifa 内置自动清理（磁盘 < 5%）**
- 自动删除最旧的文件
- 定时脚本作为主动清理，内置清理作为兜底

---

**完整文档**: [CLEANUP_GUIDE.md](CLEANUP_GUIDE.md)
**脚本位置**: `/opt/jifa/scripts/cleanup-old-files.sh`
