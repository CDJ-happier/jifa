# Jifa Docker 启动脚本使用说明

## 脚本功能

`jifa.sh` 是一个用于启动 Eclipse Jifa 分析工具的 Docker 容器启动脚本，支持数据持久化和大文件上传。

## 参数说明

### 基本参数
- `-t <tag>`: 指定 Docker 镜像标签（默认：latest）
- `-p <port>`: 指定服务端口（默认：8102）
- `-d|--data-dir <path>`: 指定数据存储目录（默认：$HOME/jifa-storage）
- `--jvm-options <options>`: 自定义 JVM 参数
- `<file1> <file2> ...`: 要分析的文件路径

### 默认配置
- **数据持久化**: 自动使用 `/data/jifa-storage` 或用户指定目录
- **大文件支持**: 默认支持 128GB 文件上传
- **端口映射**: 8102（可自定义）
- **JVM优化**: 针对72核256G服务器优化配置（180GB堆内存+G1GC）

## 使用示例

### 1. 基本启动（使用默认配置）
```bash
./jifa.sh
```
- 使用 latest 镜像
- 端口 8102
- 数据目录：`$HOME/jifa-storage`
- 支持 128GB 文件上传

### 2. 使用自定义数据目录
```bash
./jifa.sh -d /data/jifa-storage
```
- 数据持久化到 `/data/jifa-storage`
- 容器重启后文件仍然存在

### 3. 分析大文件（128GB支持）
```bash
./jifa.sh -d /data/jifa-storage /path/to/large-heapdump.hprof
```
- 自动挂载数据目录
- 支持大文件分析
- 文件分析结果持久化存储

### 4. 自定义端口和镜像版本
```bash
./jifa.sh -t v1.5 -p 8080 -d /data/jifa-storage
```
- 使用 v1.5 版本镜像
- 端口 8080
- 数据目录 `/data/jifa-storage`

### 5. 自定义 JVM 参数
```bash
./jifa.sh --jvm-options "-Xmx16g -Xms8g" -d /data/jifa-storage
```
- 设置 JVM 堆内存为 16GB
- 自定义数据目录

### 6. 分析多个文件
```bash
./jifa.sh -d /data/jifa-storage file1.hprof file2.jfr file3.gc.log
```
- 同时分析多个文件
- 所有文件共享同一个数据目录

## 数据持久化说明

### 数据目录结构
```
/data/jifa-storage/
├── uploads/          # 上传的文件
├── analysis/         # 分析结果
├── logs/            # 日志文件
└── config/          # 配置文件
```

### 持久化优势
- **容器重启不丢失**: 数据存储在宿主机目录
- **备份方便**: 可直接备份数据目录
- **多容器共享**: 多个容器可挂载同一数据目录

## 大文件上传配置

### 默认配置（72核256G优化）
- `-Xmx180g -Xms180g`: 180GB堆内存，避免动态调整开销
- `-XX:+UseG1GC`: 使用G1垃圾收集器，适合大内存场景
- `-XX:MaxGCPauseMillis=200`: 最大GC停顿时间200ms
- `-XX:G1HeapRegionSize=32m`: 大内存区域大小优化
- `-XX:ParallelGCThreads=36`: 并行GC线程数（72核的一半）
- `-XX:ConcGCThreads=12`: 并发GC线程数
- `-XX:G1ReservePercent=15`: G1保留内存百分比
- `-XX:InitiatingHeapOccupancyPercent=45`: 堆占用阈值45%
- `-XX:+UseNUMA -XX:+UseLargePages`: NUMA和大页优化
- `-XX:+AlwaysPreTouch`: 启动时预分配内存
- `spring.servlet.multipart.max-file-size=128GB`
- `spring.servlet.multipart.max-request-size=128GB`
- `-Xlog:gc:file=/jifa-storage/logs/gc.log:time,level,tags`: 简化GC日志配置（兼容性更好）

### JVM配置修复说明
- **压缩指针修复**: 移除了`-XX:+UseCompressedOops`和`-XX:+UseCompressedClassPointers`选项，因为180GB堆内存超过了32GB的压缩指针限制
- **GC日志修复**: 简化了`-Xlog`语法，解决了之前的语法错误
- **目录创建**: 脚本现在会自动创建日志目录`/jifa-storage/logs/`
- **兼容性**: 新配置在所有Java版本中都能正常工作
- **大内存优化**: 针对180GB堆内存进行了专门优化，避免压缩指针冲突

### 警告说明
- **Spring日志警告**: "Standard Commons Logging discovery in action with spring-jcl" 是正常的Spring日志框架初始化信息，可以忽略
- **压缩指针警告**: 已通过移除相关选项解决，不会再出现"Max heap size too large for Compressed Oops"警告

### 自定义配置
如需调整文件大小限制或JVM参数，使用 `--jvm-options` 参数：
```bash
# 调整文件大小限制
./jifa.sh --jvm-options "-Dspring.servlet.multipart.max-file-size=256GB -Dspring.servlet.multipart.max-request-size=256GB"

# 自定义JVM参数（覆盖默认配置）
./jifa.sh --jvm-options "-Xmx200g -Xms200g -XX:+UseG1GC -XX:MaxGCPauseMillis=150"
```

### 72核256G服务器优化说明
基于您的硬件配置，默认JVM参数已针对以下场景优化：
1. **内存分配**: 180GB堆内存（为系统预留76GB）
2. **GC策略**: G1GC适合大内存，并行GC线程充分利用72核
3. **性能优化**: NUMA、大页、预分配等高级特性
4. **监控支持**: 启用GC日志记录到数据目录

## 安全考虑

### 数据安全
- 数据存储在宿主机，容器无状态
- 支持定期备份数据目录
- 可设置目录权限控制访问

### 网络安全
- 默认端口 8102，可自定义
- 建议配置防火墙规则
- 内部网络访问建议使用 VPN

## 性能优化建议

### 硬件配置（72核256G优化）
- **CPU**: 72核（已优化并行GC线程36个）
- **内存**: 256GB（已配置180GB堆内存，为系统预留76GB）
- **存储**: SSD 硬盘，至少 1TB 可用空间（大文件分析需要）
- **网络**: 建议万兆网络，大文件上传需要高带宽

### 系统配置（72核256G优化）
```bash
# 增加系统文件描述符限制（大并发场景）
echo "fs.file-max = 1000000" >> /etc/sysctl.conf

# 增加用户进程限制
echo "* soft nofile 1000000" >> /etc/security/limits.conf
echo "* hard nofile 1000000" >> /etc/security/limits.conf

# 大页内存配置（提升内存访问性能）
echo "vm.nr_hugepages = 1024" >> /etc/sysctl.conf

# 网络优化（大文件上传）
echo "net.core.rmem_max = 67108864" >> /etc/sysctl.conf
echo "net.core.wmem_max = 67108864" >> /etc/sysctl.conf
echo "net.ipv4.tcp_rmem = 4096 87380 67108864" >> /etc/sysctl.conf
echo "net.ipv4.tcp_wmem = 4096 65536 67108864" >> /etc/sysctl.conf

# 内存管理优化
echo "vm.swappiness = 10" >> /etc/sysctl.conf
echo "vm.dirty_ratio = 15" >> /etc/sysctl.conf
echo "vm.dirty_background_ratio = 5" >> /etc/sysctl.conf
```

### NUMA优化（多CPU架构）
```bash
# 启用NUMA平衡
echo 0 > /proc/sys/kernel/numa_balancing

# 绑定进程到NUMA节点（可选）
numactl --cpunodebind=0 --membind=0 ./jifa.sh
```

## 故障排除

### 常见问题

1. **权限错误**
   ```bash
   # 确保数据目录可写
   chmod 755 /data/jifa-storage
   chown $USER:$USER /data/jifa-storage
   ```

2. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep 8102
   # 使用不同端口
   ./jifa.sh -p 8103
   ```

3. **磁盘空间不足**
   ```bash
   # 检查磁盘空间
   df -h /data/jifa-storage
   # 清理旧数据
   rm -rf /data/jifa-storage/analysis/old-*
   ```

## 监控和维护

### 日志查看
```bash
# 查看容器日志
docker logs <container-id>

# 查看数据目录使用情况
du -sh /data/jifa-storage/*
```

### 定期维护
- 定期清理过期的分析结果
- 监控磁盘空间使用情况
- 备份重要分析数据

## 环境要求

- Docker 20.10+
- 至少 4GB 可用内存
- 至少 100GB 可用磁盘空间
- Linux/macOS 系统

## 联系支持

如有问题请参考：
- Eclipse Jifa 官方文档
- Docker 官方文档
- 系统管理员