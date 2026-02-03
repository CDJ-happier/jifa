# Jifa 生产环境部署文档

## 服务器配置
- CPU: 72核
- 内存: 256GB
- 数据盘: /data
- 最大上传文件: 128GB

## 部署步骤

### 1. 准备 Java 环境

Jifa 需要 Java 17 或更高版本。为了让 systemd 服务能正常运行，需要将 Java 安装到系统目录。

**方法1：复制现有 Java 到系统目录（推荐）**
```bash
# 如果你已经有 Java 17，可以复制到系统目录
sudo cp -r /path/to/your/java17 /opt/java17-jifa
sudo chown -R root:root /opt/java17-jifa
sudo chmod -R 755 /opt/java17-jifa
```

**方法2：安装系统级 Java**
```bash
# CentOS/RHEL
sudo yum install java-17-openjdk-devel

# Ubuntu/Debian
sudo apt install openjdk-17-jdk
```

验证 Java 安装：
```bash
/opt/java17-jifa/bin/java -version
```

### 2. 创建 Jifa 用户
```bash
sudo useradd -r -m -s /bin/bash jifa
```

### 3. 创建目录结构
```bash
sudo mkdir -p /data/jifa/storage
sudo mkdir -p /data/jifa/app
sudo mkdir -p /data/jifa/logs
sudo mkdir -p /data/jifa/config
sudo chown -R jifa:jifa /data/jifa
```

### 4. 解压应用
```bash
sudo tar -xf server/build/distributions/jifa.tar -C /data/jifa/app
sudo chown -R jifa:jifa /data/jifa/app
```

### 5. 创建配置文件
配置文件位置: `/data/jifa/config/application.yml`

内容见 `config/application-production.yml`

### 6. 创建启动脚本
启动脚本位置: `/data/jifa/start-jifa.sh`

内容见 `scripts/start-jifa.sh`

**重要**: 启动脚本中必须包含 Java 环境配置：
```bash
JAVA_HOME="/opt/java17-jifa"
export PATH="$JAVA_HOME/bin:$PATH"
```

### 7. 创建 systemd 服务
服务文件位置: `/etc/systemd/system/jifa.service`

内容见 `systemd/jifa.service`

### 8. 启动服务
```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable jifa

# 启动服务
sudo systemctl start jifa

# 查看服务状态
sudo systemctl status jifa

# 查看日志
sudo journalctl -u jifa -f
```

## 验证部署

### 检查服务状态
```bash
sudo systemctl status jifa
```

### 检查端口监听
```bash
sudo netstat -tlnp | grep 8102
# 或
sudo ss -tlnp | grep 8102
```

### 检查日志
```bash
# 查看系统日志
sudo journalctl -u jifa -n 100 --no-pager

# 查看应用日志
sudo tail -f /data/jifa-logs/jifa.log
```

### 测试访问
```bash
curl http://localhost:8102
```

### 测试文件上传
浏览器访问: http://服务器IP:8102

## 服务管理命令

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

# 禁用开机自启
sudo systemctl disable jifa

# 启用开机自启
sudo systemctl enable jifa
```

## 性能调优说明

### JVM 参数说明
- `-Xmx180g -Xms180g`: 堆内存设置为180GB（预留部分给系统和堆外内存）
- `-XX:+UseG1GC`: 使用G1垃圾收集器，适合大堆内存
- `-XX:MaxGCPauseMillis=200`: GC最大暂停时间200ms
- `-XX:G1HeapRegionSize=32m`: G1区域大小32MB（大堆推荐）
- `-XX:ParallelGCThreads=36`: 并行GC线程数（一般是CPU核心数的一半）
- `-XX:ConcGCThreads=12`: 并发GC线程数（一般是ParallelGCThreads的1/3）
- `-XX:G1ReservePercent=15`: 预留15%堆内存防止晋升失败
- `-XX:InitiatingHeapOccupancyPercent=45`: 堆占用45%时启动并发标记
- `-XX:+UseNUMA`: 启用NUMA优化（多socket服务器）
- `-XX:+UseLargePages`: 使用大页内存
- `-XX:+AlwaysPreTouch`: 启动时预分配内存
- `-XX:+UseStringDeduplication`: 字符串去重（节省内存）

### 操作系统调优
需要配置大页内存（在 `/etc/sysctl.conf` 中）:
```bash
# 计算需要的大页数量（180GB / 2MB per page）
# 180 * 1024 / 2 = 92160 pages
vm.nr_hugepages = 92160
```

应用后重启系统或执行:
```bash
sudo sysctl -p
```

## 故障排查

### 服务无法启动
1. 检查 Java 是否安装: `/opt/java17-jifa/bin/java -version`
2. 检查 jifa 用户能否访问 Java: `sudo -u jifa /opt/java17-jifa/bin/java -version`
3. 检查用户权限: `ls -la /data/jifa`
4. 检查启动脚本中的 JAVA_HOME 配置
5. 查看详细日志: `sudo journalctl -u jifa -n 100`

### 端口被占用
```bash
sudo lsof -i :8102
```

### 内存不足
检查实际内存使用:
```bash
free -h
```

### 文件上传失败
1. 检查磁盘空间: `df -h /data`
2. 检查配置文件中的文件大小限制
3. 检查 nginx/代理服务器的上传限制（如果有）

## 数据备份

### 备份整个 Jifa 目录
```bash
sudo tar -czf jifa-backup-$(date +%Y%m%d).tar.gz /data/jifa
```

### 备份配置和数据（不含应用）
```bash
sudo tar -czf jifa-data-backup-$(date +%Y%m%d).tar.gz /data/jifa/storage /data/jifa/config /etc/systemd/system/jifa.service
```

## 更新升级

1. 停止服务: `sudo systemctl stop jifa`
2. 备份当前版本: `sudo cp -r /data/jifa/app /data/jifa/app.backup.$(date +%Y%m%d)`
3. 部署新版本: 解压新的 tar 包到 `/data/jifa/app`
4. 启动服务: `sudo systemctl start jifa`
5. 验证服务: `sudo systemctl status jifa`

## 安全建议

1. 配置防火墙仅允许必要端口访问
2. 定期更新 Java 运行时
3. 定期备份数据
4. 监控磁盘空间使用情况
5. 配置日志轮转避免日志文件过大
