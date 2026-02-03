# Jifa 快速参考卡片

## 🎯 一句话总结
Jifa 已部署在 /data/jifa/，使用 systemd 管理，支持 128GB 文件上传，180GB 堆内存优化。

## 📍 关键路径

| 项目 | 路径 |
|------|------|
| 应用根目录 | /data/jifa/ |
| 数据存储 | /data/jifa/storage/ |
| 日志文件 | /data/jifa/logs/ |
| 配置文件 | /data/jifa/config/application.yml |
| 启动脚本 | /data/jifa/start-jifa.sh |
| Java 环境 | /opt/java17-jifa/bin/java |
| systemd 服务 | /etc/systemd/system/jifa.service |
| 部署文档 | /opt/jifa/deployment/ |

## 🚀 常用命令

### 服务管理
```bash
sudo systemctl start jifa       # 启动
sudo systemctl stop jifa        # 停止
sudo systemctl restart jifa     # 重启
sudo systemctl status jifa      # 状态
sudo systemctl enable jifa      # 启用开机自启（已配置）
sudo systemctl disable jifa     # 禁用开机自启
```

### 日志查看
```bash
sudo journalctl -u jifa -f                  # 实时系统日志
sudo journalctl -u jifa -n 100              # 最近 100 行
sudo tail -f /data/jifa/logs/jifa.log      # 实时应用日志
sudo tail -f /data/jifa/logs/gc.log        # 实时 GC 日志
```

### 验证和诊断
```bash
bash /opt/jifa/deployment/scripts/verify.sh              # 验证部署
sudo netstat -tlnp | grep 8102                          # 检查端口
curl http://localhost:8102                              # 测试访问
ps aux | grep jifa                                      # 查看进程
du -sh /data/jifa/storage/                              # 查看存储空间
```

## ⚙️ 配置修改

### 修改文件上传限制
```bash
sudo vi /data/jifa/config/application.yml
# 修改 max-file-size 和 max-request-size
sudo systemctl restart jifa
```

### 修改 JVM 参数
```bash
sudo vi /data/jifa/start-jifa.sh
# 修改 JVM_OPTS 部分
sudo systemctl restart jifa
```

### 修改端口
```bash
sudo vi /data/jifa/config/application.yml
# 修改 server.port
sudo systemctl restart jifa
```

## 📊 监控指标

```bash
# 内存使用
sudo systemctl status jifa | grep Memory

# CPU 使用
sudo systemctl status jifa | grep CPU

# 磁盘空间
df -h /data

# 进程详情
ps aux | grep jifa | grep -v grep
```

## 🔧 故障排查

### 服务无法启动
```bash
# 1. 查看详细日志
sudo journalctl -u jifa -n 100 --no-pager

# 2. 检查 Java
sudo -u jifa /opt/java17-jifa/bin/java -version

# 3. 检查权限
ls -la /data/jifa/

# 4. 手动测试启动
cd /data/jifa && sudo -u jifa bash start-jifa.sh
```

### 端口被占用
```bash
# 查找占用进程
sudo lsof -i :8102

# 杀死进程（谨慎！）
sudo kill -9 <PID>
```

### 内存不足
```bash
# 查看内存使用
free -h

# 调整 JVM 参数
sudo vi /data/jifa/start-jifa.sh
# 减小 -Xmx 和 -Xms 值
```

## 💾 备份恢复

### 快速备份
```bash
# 备份所有数据和配置
sudo tar -czf jifa-backup-$(date +%Y%m%d-%H%M).tar.gz /data/jifa

# 仅备份数据
sudo tar -czf jifa-data-$(date +%Y%m%d-%H%M).tar.gz /data/jifa/storage
```

### 恢复
```bash
# 停止服务
sudo systemctl stop jifa

# 恢复备份
sudo tar -xzf jifa-backup-YYYYMMDD-HHMM.tar.gz -C /

# 修复权限
sudo chown -R jifa:jifa /data/jifa

# 启动服务
sudo systemctl start jifa
```

## 📈 性能优化

当前配置（72C256G 服务器）：
- 堆内存: 180GB
- GC: G1GC
- 并行线程: 36
- 并发线程: 12

如需调整，编辑 `/data/jifa/start-jifa.sh` 中的 `JVM_OPTS`。

## 🌐 访问信息

- **URL**: http://21.6.180.85:8102
- **用户**: jifa
- **主目录**: /home/jifa
- **工作目录**: /data/jifa

## 📞 获取帮助

1. 查看详细文档: `/opt/jifa/deployment/INDEX.md`
2. 运行验证脚本: `bash /opt/jifa/deployment/scripts/verify.sh`
3. 查看部署报告: `cat /opt/jifa/DEPLOYMENT_COMPLETE.md`

---

**提示**: 将此文件加入书签以便快速查阅！
