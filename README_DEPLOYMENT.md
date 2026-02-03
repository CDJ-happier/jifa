# Jifa 生产环境部署

## ✅ 部署状态：已完成

本 Jifa 实例已成功部署到生产环境。

- **访问地址**: http://21.6.180.85:8102
- **部署目录**: /data/jifa/
- **文档位置**: /opt/jifa/deployment/

## 📚 文档

**从这里开始**: [deployment/INDEX.md](deployment/INDEX.md)

或查看：
- [deployment/README.md](deployment/README.md) - 快速开始
- [deployment/SUMMARY.md](deployment/SUMMARY.md) - 部署总结
- [DEPLOYMENT_COMPLETE.md](DEPLOYMENT_COMPLETE.md) - 完整部署报告

## 🚀 快速命令

```bash
# 查看服务状态
sudo systemctl status jifa

# 查看日志
sudo journalctl -u jifa -f

# 重启服务
sudo systemctl restart jifa

# 验证部署
bash deployment/scripts/verify.sh
```

## 📊 核心配置

- **数据存储**: /data/jifa/storage/ (持久化)
- **文件上传**: 最大 128GB
- **内存配置**: 180GB 堆内存
- **服务管理**: systemd (开机自启)

## 📞 需要帮助？

查看 [deployment/](deployment/) 目录下的完整文档。
