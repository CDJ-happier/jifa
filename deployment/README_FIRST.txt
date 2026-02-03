╔══════════════════════════════════════════════════════════╗
║                                                          ║
║             Jifa 生产环境部署完成                        ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

📊 服务状态: ✅ 运行中
🌐 访问地址: http://21.6.180.85:8080
📁 部署目录: /data/jifa/
📚 文档位置: /opt/jifa/deployment/

════════════════════════════════════════════════════════════

📖 重要文档（推荐阅读顺序）

1️⃣  INDEX.md                     - 文档索引（从这里开始）
2️⃣  QUICK_REFERENCE.md           - 快速参考卡片
3️⃣  QUICKSTART_AUTOMATION.md     - 自动化分析快速指南 🔥
4️⃣  API_REFERENCE.md             - API 完整参考文档 📚
5️⃣  CONFIGURATION_PRIORITY.md    - 配置优先级说明 ⭐
6️⃣  JAVA_SETUP.md                - Java 环境配置详解
7️⃣  SUMMARY.md                   - 部署总结

════════════════════════════════════════════════════════════

🚀 快速命令

  sudo systemctl status jifa      # 查看状态
  sudo systemctl restart jifa     # 重启服务
  sudo journalctl -u jifa -f      # 查看日志

════════════════════════════════════════════════════════════

✅ 核心功能

  ✓ 数据持久化: /data/jifa/storage/
  ✓ 128GB 文件上传
  ✓ 180GB 堆内存优化
  ✓ systemd 自动管理
  ✓ 开机自启

════════════════════════════════════════════════════════════

❓ 常见问题

Q: 如何修改端口？
A: 编辑 start-jifa.sh 和 application.yml，同步修改两处

Q: 如何修改文件上传限制？
A: 编辑 /data/jifa/config/application.yml

Q: 配置文件是否生效？
A: 查看 CONFIGURATION_PRIORITY.md 了解详情

════════════════════════════════════════════════════════════

完整文档: cat INDEX.md
