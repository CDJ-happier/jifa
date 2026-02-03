# Jifa 部署总结

## 部署状态

✅ **部署成功** - 服务已正常运行

- **服务状态**: Active (running)
- **端口监听**: 8102
- **内存使用**: ~188GB (配置 180GB)
- **进程 PID**: 运行中
- **访问地址**: http://21.6.180.85:8102

## 关键配置

### 目录结构
```
/data/jifa/
├── app/              # 应用程序
├── storage/          # 数据存储（支持 128GB 文件上传）
├── logs/             # 日志文件（jifa.log, gc.log）
├── config/           # 配置文件
└── start-jifa.sh     # 启动脚本
```

### Java 环境
- **位置**: `/opt/java17-jifa`
- **版本**: OpenJDK 17.0.18 (TencentKonaJDK)
- **配置方式**: 在启动脚本中设置 JAVA_HOME

### JVM 参数（72C256G 服务器优化）
- 堆内存: `-Xmx180g -Xms180g`
- GC: G1GC
- 并行 GC 线程: 36
- 并发 GC 线程: 12
- NUMA、大页内存、字符串去重等优化已启用

### 文件上传限制
- 最大文件大小: **128GB**
- 配置位置: `/data/jifa/config/application.yml`

## 服务管理

### 常用命令
```bash
# 启动服务
sudo systemctl start jifa

# 停止服务
sudo systemctl stop jifa

# 重启服务
sudo systemctl restart jifa

# 查看状态
sudo systemctl status jifa

# 查看日志
sudo journalctl -u jifa -f

# 查看应用日志
sudo tail -f /data/jifa/logs/jifa.log
```

### 开机自启
已配置，服务会在系统启动时自动启动。

## 验证清单

- [x] jifa 用户已创建
- [x] 目录结构正确，权限为 jifa:jifa
- [x] Java 环境配置正确
- [x] 应用已解压到 /data/jifa/app/
- [x] 配置文件包含 128GB 上传限制
- [x] 启动脚本包含 Java 环境配置
- [x] systemd 服务已安装并启用
- [x] 服务正常运行
- [x] 端口 8102 正在监听
- [x] 磁盘空间充足（882G 可用）

## 重要提示

1. **Java 环境**: 使用系统级 Java (`/opt/java17-jifa`)，确保 jifa 用户可以访问
2. **数据持久化**: 所有数据存储在 `/data/jifa/storage/`，重启不会丢失
3. **日志轮转**: 日志会自动轮转，保留 30 天，总大小不超过 10GB
4. **性能监控**: 可通过 `sudo systemctl status jifa` 查看内存和 CPU 使用情况
5. **备份建议**: 定期备份 `/data/jifa/storage/` 和 `/data/jifa/config/`

## 文档索引

- [README.md](README.md) - 快速开始和概览
- [DEPLOYMENT.md](DEPLOYMENT.md) - 详细部署步骤和配置说明
- [JAVA_SETUP.md](JAVA_SETUP.md) - Java 环境配置详解
- [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md) - 目录结构说明

## 故障排查

如遇问题，请按以下顺序检查：

1. 查看服务状态: `sudo systemctl status jifa`
2. 查看系统日志: `sudo journalctl -u jifa -n 100`
3. 查看应用日志: `sudo tail -100 /data/jifa/logs/jifa.log`
4. 运行验证脚本: `bash /opt/jifa/deployment/scripts/verify.sh`
5. 检查 Java 环境: `sudo -u jifa /opt/java17-jifa/bin/java -version`

## 下一步

服务已成功部署并运行！可以：

1. 访问 Web 界面: http://21.6.180.85:8102
2. 上传分析文件（支持最大 128GB）
3. 配置防火墙规则（如需要）
4. 设置监控和告警（建议）
5. 配置反向代理（如 Nginx，可选）

## 部署完成时间

2026-02-03 14:15:00
