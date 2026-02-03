# Jifa 生产环境部署完成报告

## ✅ 部署状态：成功

**部署时间**: 2026-02-03  
**服务器**: 21.6.180.85 (72C256G)  
**部署目录**: /data/jifa/

---

## 📊 服务状态

```
● jifa.service - Jifa - Java Issues Finding Assistant
     Status: ✅ Active (running)
     Port: 8102 (监听中)
     Memory: ~188GB
     PID: Running
     Access: http://21.6.180.85:8102
```

---

## 🎯 已实现的需求

### 1. ✅ 本地数据盘存储
- **路径**: `/data/jifa/storage/`
- **特点**: 数据持久化，重启不丢失

### 2. ✅ 128GB 文件上传支持
- **配置位置**: `/data/jifa/config/application.yml`
- **参数**:
  ```yaml
  spring.servlet.multipart:
    max-file-size: 128GB
    max-request-size: 128GB
  ```

### 3. ✅ 性能优化（72C256G 服务器）
- **堆内存**: 180GB (`-Xmx180g -Xms180g`)
- **GC**: G1GC
- **并行 GC 线程**: 36
- **并发 GC 线程**: 12
- **其他优化**: NUMA、大页内存、字符串去重、Always PreTouch
- **GC 日志**: `/data/jifa/logs/gc.log`

### 4. ✅ systemd 服务管理
- **服务名**: jifa.service
- **用户**: jifa
- **开机自启**: 已启用
- **自动重启**: 异常时自动重启
- **日志集成**: journald

### 5. ✅ 数据持久化
- **存储目录**: `/data/jifa/storage/`
- **所有者**: jifa:jifa
- **特点**: 重启不影响已上传文件和分析结果

---

## 📁 目录结构

```
/data/jifa/
├── app/                    # 应用程序
│   └── jifa/
│       ├── bin/
│       └── lib/jifa.jar
├── storage/                # 数据存储（持久化）
│   └── temp/              # 临时上传目录
├── logs/                   # 日志文件
│   ├── jifa.log           # 应用日志
│   └── gc.log             # GC 日志
├── config/                 # 配置文件
│   └── application.yml    # 主配置（含 128GB 上传限制）
└── start-jifa.sh          # 启动脚本（含 Java 环境配置）

/opt/java17-jifa/          # 系统级 Java 环境
└── bin/java               # Java 17.0.18

/etc/systemd/system/
└── jifa.service           # systemd 服务配置
```

---

## 🔧 配置要点

### Java 环境
- **位置**: `/opt/java17-jifa`
- **版本**: OpenJDK 17.0.18 (TencentKonaJDK)
- **配置方式**: 
  - 启动脚本中设置 `JAVA_HOME`
  - systemd 环境变量（双保险）

### JVM 参数优化
```bash
-Xmx180g -Xms180g
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-XX:G1HeapRegionSize=32m
-XX:ParallelGCThreads=36
-XX:ConcGCThreads=12
-XX:G1ReservePercent=15
-XX:InitiatingHeapOccupancyPercent=45
-XX:+UseNUMA
-XX:+UseLargePages
-XX:+AlwaysPreTouch
-XX:+UseStringDeduplication
```

---

## 📝 管理命令

### 服务管理
```bash
sudo systemctl start jifa      # 启动
sudo systemctl stop jifa       # 停止
sudo systemctl restart jifa    # 重启
sudo systemctl status jifa     # 状态
```

### 日志查看
```bash
# 系统日志（实时）
sudo journalctl -u jifa -f

# 应用日志（实时）
sudo tail -f /data/jifa/logs/jifa.log

# GC 日志
sudo tail -f /data/jifa/logs/gc.log
```

### 验证部署
```bash
bash /opt/jifa/deployment/scripts/verify.sh
```

---

## 📚 文档位置

所有部署文档位于: `/opt/jifa/deployment/`

- **INDEX.md** - 文档索引（推荐从这里开始）
- **README.md** - 快速开始
- **DEPLOYMENT.md** - 详细部署步骤
- **JAVA_SETUP.md** - Java 环境配置详解
- **DIRECTORY_STRUCTURE.md** - 目录结构说明
- **SUMMARY.md** - 部署总结

---

## ✅ 验证清单

- [x] jifa 用户已创建
- [x] 目录结构正确 (/data/jifa/)
- [x] Java 环境配置 (/opt/java17-jifa)
- [x] 应用已部署
- [x] 配置文件包含 128GB 上传限制
- [x] 启动脚本包含 Java 环境配置
- [x] systemd 服务已安装
- [x] 服务已启用（开机自启）
- [x] 服务正常运行
- [x] 端口 8102 正在监听
- [x] 日志文件已生成
- [x] 磁盘空间充足（882G 可用）

---

## 🌐 访问服务

**Web 界面**: http://21.6.180.85:8102

可以开始上传和分析文件了！

---

## 🔍 故障排查

如遇问题，按以下顺序检查：

1. 服务状态: `sudo systemctl status jifa`
2. 系统日志: `sudo journalctl -u jifa -n 100`
3. 应用日志: `sudo tail -100 /data/jifa/logs/jifa.log`
4. 验证脚本: `bash /opt/jifa/deployment/scripts/verify.sh`
5. Java 环境: `sudo -u jifa /opt/java17-jifa/bin/java -version`

详细故障排查指南请查看 `/opt/jifa/deployment/DEPLOYMENT.md`

---

## 💾 备份建议

### 定期备份数据
```bash
# 备份整个 Jifa 目录
sudo tar -czf jifa-backup-$(date +%Y%m%d).tar.gz /data/jifa

# 仅备份数据和配置
sudo tar -czf jifa-data-$(date +%Y%m%d).tar.gz /data/jifa/storage /data/jifa/config
```

### 备份配置文件
```bash
sudo cp /etc/systemd/system/jifa.service jifa.service.backup
```

---

## 🚀 后续步骤

1. ✅ 服务已部署并运行
2. 🔜 配置防火墙规则（如需要）
3. 🔜 设置监控和告警
4. 🔜 配置反向代理（Nginx，可选）
5. 🔜 定期备份数据

---

## 📞 技术支持

- **项目主页**: https://eclipse-jifa.github.io/jifa/
- **GitHub**: https://github.com/eclipse/jifa
- **部署文档**: /opt/jifa/deployment/

---

**部署完成！感谢使用 Jifa！** 🎉
