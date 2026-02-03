# Jifa 目录结构

```
/data/jifa/                          # Jifa 根目录
├── app/                             # 应用程序目录
│   └── jifa/                        # 解压的应用
│       ├── bin/                     # 启动脚本
│       │   └── jifa                 # 原始启动脚本
│       └── lib/                     # 应用库文件
│           └── jifa.jar             # 主程序 JAR
├── storage/                         # 数据存储目录
│   ├── temp/                        # 临时文件目录（上传缓存）
│   └── [用户上传的文件和分析结果]
├── logs/                            # 日志目录
│   ├── jifa.log                     # 应用日志
│   └── gc.log                       # GC 日志
├── config/                          # 配置目录
│   └── application.yml              # 应用配置文件
└── start-jifa.sh                    # 启动脚本（由 deploy.sh 复制）

/etc/systemd/system/
└── jifa.service                     # systemd 服务配置
```

## 目录说明

### /data/jifa/app/
应用程序安装目录，包含从构建产物解压出的所有应用文件。

### /data/jifa/storage/
数据持久化目录，存储用户上传的文件和分析结果。
- 重启不会丢失数据
- 需要定期备份
- 支持最大 128GB 单文件

### /data/jifa/logs/
日志文件目录
- `jifa.log`: 应用运行日志
- `gc.log`: JVM GC 日志
- 日志会自动轮转，最多保留 30 天，总大小不超过 10GB

### /data/jifa/config/
配置文件目录
- `application.yml`: 主配置文件，包含存储路径、文件大小限制等配置

### /data/jifa/start-jifa.sh
启动脚本，包含所有 JVM 参数和应用配置，由 systemd 调用。

## 磁盘空间建议

根据 128GB 文件上传需求，建议：
- `/data` 分区至少: 500GB+
- 建议: 1TB+ （预留空间给多个文件和分析结果）

## 权限

所有 `/data/jifa/` 下的文件和目录所有者应为 `jifa:jifa`。

```bash
sudo chown -R jifa:jifa /data/jifa
```
