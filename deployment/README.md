# Jifa 生产环境部署包

本部署包包含了 Jifa 在生产环境部署所需的所有配置文件和脚本。

## 快速开始

### 前置条件
1. 已执行 `sudo bash jifa-jpackage.sh` 成功构建
2. 确保 `server/build/distributions/jifa.tar` 存在
3. **已安装 Java 17 到系统目录 `/opt/java17-jifa`**
4. 服务器配置: 72C256G

### Java 环境准备

**重要**: 必须将 Java 安装到系统目录，确保 jifa 用户可以访问：

```bash
# 复制 Java 到系统目录
sudo cp -r /path/to/your/java17 /opt/java17-jifa
sudo chown -R root:root /opt/java17-jifa
sudo chmod -R 755 /opt/java17-jifa

# 验证
/opt/java17-jifa/bin/java -version
```

### 一键部署

```bash
sudo bash deployment/scripts/deploy.sh
```

该脚本会自动：
1. 创建 jifa 用户
2. 创建目录结构 `/data/jifa/`
3. 解压应用到 `/data/jifa/app/`
4. 配置文件、启动脚本
5. 安装 systemd 服务
6. 启用开机自启

### 启动服务

```bash
sudo systemctl start jifa
```

### 验证部署

```bash
bash deployment/scripts/verify.sh
```

## 文件说明

```
deployment/
├── README.md                        # 本文件
├── DEPLOYMENT.md                    # 详细部署文档
├── DIRECTORY_STRUCTURE.md           # 目录结构说明
├── config/
│   └── application-production.yml   # 生产环境配置
├── scripts/
│   ├── deploy.sh                    # 自动部署脚本
│   ├── start-jifa.sh                # 启动脚本模板
│   └── verify.sh                    # 部署验证脚本
└── systemd/
    └── jifa.service                 # systemd 服务配置
```

## 主要特性

### 1. 数据持久化
- 所有数据存储在 `/data/jifa/storage/`
- 重启不丢失数据

### 2. 大文件支持
- 支持最大 128GB 文件上传
- 配置在 `application-production.yml` 中

### 3. 性能优化
- JVM 参数针对 72C256G 服务器优化
- 使用 G1 GC，堆内存 180GB
- 启用 NUMA、大页内存等优化

### 4. systemd 管理
- 开机自启
- 异常自动重启
- 日志集成到 journald

## 常用命令

### 服务管理
```bash
sudo systemctl start jifa      # 启动
sudo systemctl stop jifa       # 停止
sudo systemctl restart jifa    # 重启
sudo systemctl status jifa     # 查看状态
```

### 日志查看
```bash
sudo journalctl -u jifa -f     # 系统日志（实时）
sudo tail -f /data/jifa/logs/jifa.log  # 应用日志（实时）
```

### 访问服务
```bash
http://服务器IP:8102
```

## 文档

- [DEPLOYMENT.md](DEPLOYMENT.md) - 完整部署文档
- [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md) - 目录结构说明

## 故障排查

如果部署失败或服务无法启动，请查看：
1. 系统日志: `sudo journalctl -u jifa -n 100`
2. 应用日志: `sudo tail -f /data/jifa/logs/jifa.log`
3. 执行验证: `bash deployment/scripts/verify.sh`

## 目录结构

部署后的目录结构：

```
/data/jifa/
├── app/           # 应用程序
├── storage/       # 数据存储（持久化）
├── logs/          # 日志文件
├── config/        # 配置文件
└── start-jifa.sh  # 启动脚本
```

所有文件所有者: `jifa:jifa`
