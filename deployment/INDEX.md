# Jifa 部署文档索引

欢迎使用 Jifa 生产环境部署包！

## 快速导航

### 🚀 快速开始
- [README.md](README.md) - 快速部署指南（推荐从这里开始）

### 📖 详细文档
- [DEPLOYMENT.md](DEPLOYMENT.md) - 完整部署步骤和配置说明
- [JAVA_SETUP.md](JAVA_SETUP.md) - Java 环境配置详解（重要！）
- [CONFIGURATION_PRIORITY.md](CONFIGURATION_PRIORITY.md) - 配置优先级和生效说明 ⭐
- [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md) - 目录结构说明
- [SUMMARY.md](SUMMARY.md) - 部署总结和验证清单

### 📂 配置文件
- [config/application-production.yml](config/application-production.yml) - 生产环境配置（128GB 上传）

### 🔧 脚本工具
- [scripts/deploy.sh](scripts/deploy.sh) - 自动部署脚本
- [scripts/start-jifa.sh](scripts/start-jifa.sh) - 启动脚本模板
- [scripts/verify.sh](scripts/verify.sh) - 部署验证脚本

### ⚙️ 系统集成
- [systemd/jifa.service](systemd/jifa.service) - systemd 服务配置

## 部署流程

```
1. 准备 Java 环境 → 参考 JAVA_SETUP.md
2. 执行构建 → sudo bash jifa-jpackage.sh
3. 自动部署 → sudo bash deployment/scripts/deploy.sh
4. 启动服务 → sudo systemctl start jifa
5. 验证部署 → bash deployment/scripts/verify.sh
```

## 核心特性

✅ 数据持久化 - 存储在 /data/jifa/storage/
✅ 128GB 文件上传 - 支持大型堆转储文件
✅ 性能优化 - 针对 72C256G 服务器优化
✅ systemd 管理 - 开机自启、自动重启
✅ 日志轮转 - 自动管理日志大小

## 常见问题

**Q: 服务启动失败，提示 "java: not found"？**
A: 查看 [JAVA_SETUP.md](JAVA_SETUP.md)，确保 Java 安装在 /opt/java17-jifa

**Q: 命令行参数和配置文件都有配置，哪个生效？**
A: 查看 [CONFIGURATION_PRIORITY.md](CONFIGURATION_PRIORITY.md)，了解 Spring Boot 配置优先级

**Q: 如何修改文件上传大小限制？**
A: 编辑 /data/jifa/config/application.yml，修改 max-file-size 和 max-request-size，然后重启服务

**Q: 如何查看服务日志？**
A: `sudo journalctl -u jifa -f` 或 `sudo tail -f /data/jifa/logs/jifa.log`

**Q: 数据存储在哪里？**
A: /data/jifa/storage/ - 所有上传文件和分析结果都在这里

## 获取帮助

遇到问题？

1. 查看 [DEPLOYMENT.md](DEPLOYMENT.md) 的"故障排查"部分
2. 运行验证脚本: `bash deployment/scripts/verify.sh`
3. 查看详细日志: `sudo journalctl -u jifa -n 100`

---

**版本**: 1.0
**更新时间**: 2026-02-03
