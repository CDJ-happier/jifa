# Jifa 编译与部署指南

> **适用场景**：修改源码后，将新版本编译并部署到生产环境。

---

## 目录结构（速查）

```
/opt/jifa/                               # 源码 & 构建目录
├── jifa-jpackage.sh                     # 编译脚本
├── server/build/libs/jifa.jar           # 编译中间产物
├── server/build/distributions/jifa.tar  # 编译最终产物（用于部署）
└── deployment/
    ├── scripts/deploy.sh                # 部署脚本
    ├── systemd/jifa.service             # systemd 服务模板
    └── config/application-production.yml  # 配置模板

/data/jifa/                              # 生产运行目录
├── app/jifa/                            # 当前运行的应用（会被替换）
│   ├── lib/jifa.jar
│   └── bin/
├── app/jifa.backup.YYYYMMDD_HHMMSS/    # 旧版本备份（自动生成）
├── config/application.yml               # 运行配置（不会被覆盖）
├── storage/                             # 数据文件（不会被覆盖）
├── logs/                                # 日志文件（不会被覆盖）
└── start-jifa.sh                        # 启动脚本

/opt/java17-jifa/                        # Java 17 (TencentKona)
/etc/systemd/system/jifa.service         # systemd 服务
```

---

## 日常重新部署（4 步）

修改代码后，按以下步骤重新部署：

```bash
# 第 1 步：编译（在源码目录执行，约 10-15 分钟）
cd /opt/jifa
sudo ./jifa-jpackage.sh

# 第 2 步：停止服务
sudo systemctl stop jifa

# 第 3 步：部署（自动备份旧版本、解压新版本）
sudo bash /opt/jifa/deployment/scripts/deploy.sh

# 第 4 步：启动服务
sudo systemctl start jifa
```

**验证**：

```bash
sudo systemctl status jifa
curl -s http://localhost:8080/jifa-api/files?type=HEAP_DUMP\&page=1\&pageSize=1 | jq .
```

---

## 首次部署（全新服务器）

### 1. 安装 Java 17

Java 需安装在系统级目录，使 `jifa` 用户可访问。

```bash
# 从现有 SDKMAN 安装复制（推荐）
sudo cp -r ~/.sdkman/candidates/java/17.0.18-kona /opt/java17-jifa
sudo chown -R root:root /opt/java17-jifa
sudo chmod -R 755 /opt/java17-jifa

# 验证
/opt/java17-jifa/bin/java -version
```

或通过包管理器安装：

```bash
# CentOS/RHEL
sudo yum install java-17-openjdk-devel

# Ubuntu/Debian
sudo apt install openjdk-17-jdk
```

> 安装后如果路径不是 `/opt/java17-jifa`，需同步修改 `/data/jifa/start-jifa.sh` 和 `/etc/systemd/system/jifa.service` 中的 `JAVA_HOME`。

### 2. 编译源码

```bash
cd /opt/jifa
sudo ./jifa-jpackage.sh
```

产物位置：`/opt/jifa/server/build/distributions/jifa.tar`

### 3. 运行部署脚本

```bash
sudo bash /opt/jifa/deployment/scripts/deploy.sh
```

脚本会自动完成：
- 创建 `jifa` 用户（已存在则跳过）
- 创建 `/data/jifa/` 目录结构
- 解压应用到 `/data/jifa/app/jifa/`
- 复制初始配置文件到 `/data/jifa/config/application.yml`（已存在则跳过）

### 4. 安装 systemd 服务

```bash
sudo cp /opt/jifa/deployment/systemd/jifa.service /etc/systemd/system/jifa.service
sudo systemctl daemon-reload
sudo systemctl enable jifa   # 开机自启
```

### 5. 安装启动脚本

```bash
sudo cp /opt/jifa/deployment/scripts/start-jifa.sh /data/jifa/start-jifa.sh
sudo chmod +x /data/jifa/start-jifa.sh
sudo chown jifa:jifa /data/jifa/start-jifa.sh
```

### 6. 检查配置文件

编辑 `/data/jifa/config/application.yml`，确认以下关键项：

```yaml
jifa:
  role: standalone-worker
  storage-path: /data/jifa/storage

server:
  port: 8080
```

### 7. 启动服务

```bash
sudo systemctl start jifa
sudo systemctl status jifa
```

---

## 服务管理

```bash
sudo systemctl start jifa      # 启动
sudo systemctl stop jifa       # 停止
sudo systemctl restart jifa    # 重启
sudo systemctl status jifa     # 查看状态
sudo journalctl -u jifa -f     # 实时日志
sudo journalctl -u jifa -n 100 # 最近 100 行日志
```

---

## 回滚

如果新版本有问题，快速回滚到上一版本：

```bash
sudo systemctl stop jifa

# 查看可用备份
ls -la /data/jifa/app/jifa.backup.*

# 回滚（替换为实际备份目录名）
sudo rm -rf /data/jifa/app/jifa
sudo mv /data/jifa/app/jifa.backup.YYYYMMDD_HHMMSS /data/jifa/app/jifa

sudo systemctl start jifa
```

---

## 故障排查

### 服务无法启动

```bash
# 查看详细错误日志
sudo journalctl -u jifa -n 50 --no-pager

# 检查 Java 是否可用
sudo -u jifa /opt/java17-jifa/bin/java -version

# 检查文件权限
ls -la /data/jifa/app/jifa/lib/jifa.jar
```

### 编译失败

```bash
# 检查 Java 版本（需要 17+）
java -version

# 检查构建产物是否存在
ls -lh /opt/jifa/server/build/distributions/jifa.tar
```

### 端口被占用

```bash
sudo lsof -i :8080
```

### 磁盘空间不足

```bash
df -h /data
# 清理旧备份（保留最近 2 个）
ls -t /data/jifa/app/jifa.backup.* | tail -n +3 | xargs sudo rm -rf
```
