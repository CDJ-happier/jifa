# Jifa 重新部署指南

修改源码后如何重新部署到生产环境。

## 快速部署（3 步）

```bash
# 1. 构建（在 /opt/jifa 目录）
cd /opt/jifa
sudo ./jifa-jpackage.sh

# 2. 停止服务
sudo systemctl stop jifa

# 3. 部署
sudo bash deployment/scripts/deploy.sh

# 4. 启动服务
sudo systemctl start jifa
```

## 详细说明

### 步骤 1: 构建

```bash
cd /opt/jifa
sudo ./jifa-jpackage.sh
```

**做了什么**:
- 执行 `./gradlew clean build -x test`
- 使用 `jpackage` 打包
- 生成 `server/build/distributions/jifa.tar`

**注意**:
- 需要 sudo 权限
- 需要 10-15 分钟（视服务器性能）
- 跳过测试 (`-x test`)

### 步骤 2: 停止服务

```bash
sudo systemctl stop jifa
```

**为什么**:
- 避免文件被占用
- 确保新版本完全替换旧版本

### 步骤 3: 部署

```bash
sudo bash deployment/scripts/deploy.sh
```

**做了什么**:
1. ✅ 检查构建产物 `jifa.tar` 是否存在
2. ✅ 备份旧版本到 `/data/jifa/app/jifa.backup.YYYYMMDD_HHMMSS`
3. ✅ 解压新版本到 `/data/jifa/app/jifa`
4. ✅ 更新启动脚本
5. ✅ 重载 systemd 配置

**保留的文件**:
- ❌ 不会覆盖 `/data/jifa/config/application.yml`
- ❌ 不会删除 `/data/jifa/storage/` 数据
- ❌ 不会删除 `/data/jifa/logs/` 日志

### 步骤 4: 启动服务

```bash
sudo systemctl start jifa
```

### 步骤 5: 验证

```bash
# 查看服务状态
sudo systemctl status jifa

# 查看启动日志
sudo journalctl -u jifa -f

# 测试 API
curl -s http://localhost:8080/jifa-api/files?type=HEAP_DUMP\&page=1\&pageSize=1 | jq .
```

---

## 快速回滚

如果新版本有问题，可以快速回滚：

```bash
# 1. 停止服务
sudo systemctl stop jifa

# 2. 查找备份
ls -la /data/jifa/app/jifa.backup.*

# 3. 回滚到备份版本
sudo rm -rf /data/jifa/app/jifa
sudo mv /data/jifa/app/jifa.backup.20260203_143000 /data/jifa/app/jifa

# 4. 启动服务
sudo systemctl start jifa
```

---

## 常见问题

### Q1: 构建失败，提示 "java: not found"

**解决**:
```bash
# 检查 Java 版本
java -version

# 如果没有 Java，安装 Java 17
# 参考 /opt/jifa/deployment/JAVA_SETUP.md
```

### Q2: 部署失败，提示 "找不到构建产物"

**原因**: `jifa-jpackage.sh` 没有执行成功

**解决**:
```bash
# 检查构建产物是否存在
ls -lh /opt/jifa/server/build/distributions/jifa.tar

# 如果不存在，重新构建
cd /opt/jifa
sudo ./jifa-jpackage.sh
```

### Q3: 服务启动失败

**检查日志**:
```bash
sudo journalctl -u jifa -n 100 --no-pager
```

**常见原因**:
- 端口 8080 被占用
- Java 环境变量未设置
- 配置文件错误

### Q4: 如何只更新配置不重新构建？

**只更新配置**:
```bash
# 1. 编辑配置
sudo vim /data/jifa/config/application.yml

# 2. 重启服务
sudo systemctl restart jifa
```

### Q5: 如何保留数据重新部署？

**数据自动保留**:
- `/data/jifa/storage/` - 数据文件（自动保留）
- `/data/jifa/config/application.yml` - 配置文件（自动保留）
- `/data/jifa/logs/` - 日志文件（自动保留）

**只有应用程序会被替换**:
- `/data/jifa/app/jifa/` - 应用程序（会被替换，旧版本备份）

---

## 部署检查清单

部署前:
- [ ] 代码已提交并测试
- [ ] 已备份重要数据
- [ ] 已通知用户服务将暂时不可用

构建阶段:
- [ ] `./jifa-jpackage.sh` 执行成功
- [ ] `server/build/distributions/jifa.tar` 存在

部署阶段:
- [ ] 服务已停止
- [ ] `deploy.sh` 执行成功
- [ ] 旧版本已备份

验证阶段:
- [ ] 服务启动成功 (`systemctl status jifa`)
- [ ] API 可以访问
- [ ] 日志无错误
- [ ] 文件上传功能正常
- [ ] 已有数据可以访问

---

## 生产环境部署建议

### 1. 滚动部署（推荐）

如果有多个节点，使用滚动部署：

```bash
# 节点 1
sudo systemctl stop jifa
sudo bash deployment/scripts/deploy.sh
sudo systemctl start jifa
# 验证节点 1 正常

# 节点 2
sudo systemctl stop jifa
sudo bash deployment/scripts/deploy.sh
sudo systemctl start jifa
# 验证节点 2 正常

# ...
```

### 2. 蓝绿部署

使用不同的端口部署新版本：

```bash
# 修改配置使用不同端口
# /data/jifa/config/application.yml
# jifa.port: 8081

# 部署新版本
sudo bash deployment/scripts/deploy.sh
sudo systemctl start jifa

# 验证新版本（8081 端口）
# 切换流量到新版本
# 停止旧版本
```

### 3. 维护窗口

在维护窗口执行：
- 凌晨 2-4 点（用户少）
- 提前通知用户
- 准备回滚方案

---

## 服务管理命令

```bash
# 查看状态
sudo systemctl status jifa

# 启动
sudo systemctl start jifa

# 停止
sudo systemctl stop jifa

# 重启
sudo systemctl restart jifa

# 查看日志（实时）
sudo journalctl -u jifa -f

# 查看日志（最近 100 行）
sudo journalctl -u jifa -n 100

# 查看日志（指定时间）
sudo journalctl -u jifa --since "2026-02-03 14:00:00"
```

---

## 目录结构

```
/opt/jifa/                                    # 源码和构建目录
├── jifa-jpackage.sh                         # 构建脚本
├── server/build/distributions/jifa.tar      # 构建产物
└── deployment/scripts/deploy.sh             # 部署脚本

/data/jifa/                                  # 生产环境目录
├── app/jifa/                                # 应用程序（会被替换）
│   ├── lib/jifa.jar
│   └── bin/Eclipse Jifa
├── app/jifa.backup.YYYYMMDD_HHMMSS/        # 旧版本备份
├── storage/                                 # 数据存储（保留）
├── config/application.yml                   # 配置文件（保留）
├── logs/                                    # 日志文件（保留）
└── start-jifa.sh                            # 启动脚本

/etc/systemd/system/jifa.service             # systemd 服务配置
```

---

## 相关文档

- [部署文档](DEPLOYMENT.md) - 首次部署完整指南
- [Java 环境](JAVA_SETUP.md) - Java 环境配置
- [配置说明](CONFIGURATION_PRIORITY.md) - 配置优先级
- [文档索引](INDEX.md) - 所有文档索引

---

**版本**: 1.0
**更新时间**: 2026-02-03
