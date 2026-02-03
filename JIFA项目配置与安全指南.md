# Eclipse Jifa 项目配置与安全指南

## 🚀 高性能服务器配置（72c256G + 1T数据盘）

### 1. 存储路径配置

**当前默认配置**: `${user.home}/jifa-storage` (系统盘)
**推荐配置**: `/data/jifa-storage` (数据盘)

#### 配置方式

**方式一：通过启动参数配置**
```bash
./jifa/bin/jifa --jifa.storage-path=/data/jifa-storage
```

**方式二：通过环境变量配置**
```bash
export JIFA_STORAGE_PATH=/data/jifa-storage
./jifa/bin/jifa
```

**方式三：Docker部署配置**
```yaml
# docker-compose.yml
version: '3.8'
services:
  jifa:
    image: eclipsejifa/jifa:latest
    ports:
      - "8102:8102"
    volumes:
      - /data/jifa-storage:/jifa-storage
    environment:
      - JIFA_STORAGE_PATH=/jifa-storage
```

### 2. JVM内存优化配置

针对256G内存服务器，建议配置：

```bash
# JVM堆内存配置（建议分配64-128G）
-Xmx128g -Xms64g

# 元空间配置
-XX:MaxMetaspaceSize=2g

# GC优化（根据实际负载选择）
-XX:+UseG1GC -XX:MaxGCPauseMillis=200
# 或者使用ZGC（适合大内存）
-XX:+UseZGC -XX:+ZGenerational

# 线程池配置
-Djifa.worker-threads=64
```

### 3. 文件上传限制配置

```yaml
# application.yml
spring:
  servlet:
    multipart:
      max-file-size: 10GB    # 单个文件最大10GB
      max-request-size: 10GB # 请求最大10GB
```

## 🔒 安全性配置

### 1. 认证授权配置

**内部访问场景推荐配置**：
```yaml
# 禁用注册，仅允许管理员创建账户
jifa:
  allow-login: true           # 启用登录
  allow-anonymous-access: false # 禁用匿名访问
  allow-registration: false   # 禁用用户注册
  admin-username: admin       # 管理员用户名
  admin-password: ${ADMIN_PASSWORD} # 从环境变量读取密码
  security-filters-enabled: true # 启用安全过滤器
```

### 2. Docker安全最佳实践

#### 容器安全配置
```yaml
# docker-compose.yml安全配置
services:
  jifa:
    # 使用非root用户运行
    user: "1000:1000"
    
    # 资源限制
    deploy:
      resources:
        limits:
          memory: 240G
          cpus: '70'
        reservations:
          memory: 64G
          cpus: '8'
    
    # 安全配置
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    
    # 只读文件系统（除存储目录外）
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid
```

#### 网络安全性
```yaml
# 仅开放必要端口
ports:
  - "8102:8102"  # 应用端口

# 使用内部网络
networks:
  jifa-internal:
    internal: true
```

### 3. 数据库安全

**生产环境建议使用外部MySQL**：
```bash
# 环境变量配置
export MYSQL_HOST=mysql.internal.company.com
export MYSQL_DATABASE=jifa
export MYSQL_USER=jifa_app
export MYSQL_PASSWORD=${DB_PASSWORD}
```

## 🗑️ 文件清理策略

### 1. 当前清理机制

**手动清理方法**：
```java
// 通过StorageService.scavenge()方法清理
storageService.scavenge(FileType.HEAP_DUMP, "file-id");
```

**清理范围**：
- ✅ 删除文件本身
- ✅ 删除对应的存储目录
- ❌ **不删除索引文件**（需要额外处理）

### 2. 自动清理方案

#### 方案一：Cron定时任务
```bash
# /etc/cron.daily/jifa-cleanup
#!/bin/bash

# 清理7天前的文件
find /data/jifa-storage -type f -mtime +7 -delete
find /data/jifa-storage -type d -empty -delete

# 清理临时文件
find /tmp -name "jifa-*" -mtime +1 -delete
```

#### 方案二：Spring Boot定时任务（推荐）

创建自动清理服务：
```java
@Component
public class JifaAutoCleanupService {
    
    @Scheduled(cron = "0 0 2 * * ?") // 每天凌晨2点执行
    public void cleanupOldFiles() {
        // 清理30天前的文件
        LocalDateTime cutoff = LocalDateTime.now().minusDays(30);
        
        // 遍历所有文件类型目录
        for (FileType fileType : FileType.values()) {
            Path typeDir = storagePath.resolve(fileType.getStorageDirectoryName());
            if (Files.exists(typeDir)) {
                try (Stream<Path> paths = Files.list(typeDir)) {
                    paths.filter(Files::isDirectory)
                         .filter(dir -> {
                             try {
                                 BasicFileAttributes attrs = Files.readAttributes(
                                     dir, BasicFileAttributes.class);
                                 return attrs.lastModifiedTime().toInstant()
                                         .isBefore(cutoff.toInstant(ZoneOffset.UTC));
                             } catch (IOException e) {
                                 return false;
                             }
                         })
                         .forEach(dir -> {
                             try {
                                 FileUtils.deleteDirectory(dir.toFile());
                                 log.info("Deleted old file directory: {}", dir);
                             } catch (IOException e) {
                                 log.error("Failed to delete directory: {}", dir, e);
                             }
                         });
                } catch (IOException e) {
                    log.error("Error listing files in directory: {}", typeDir, e);
                }
            }
        }
    }
}
```

### 3. 磁盘空间监控

```bash
# 监控脚本 /usr/local/bin/jifa-disk-monitor.sh
#!/bin/bash

THRESHOLD=80  # 磁盘使用率阈值
DATA_DIR="/data/jifa-storage"

usage=$(df "$DATA_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')

if [ "$usage" -gt "$THRESHOLD" ]; then
    # 触发清理
    find "$DATA_DIR" -type f -mtime +3 -delete
    find "$DATA_DIR" -type d -empty -delete
    
    # 发送告警
    echo "Jifa storage usage $usage% - triggered cleanup" | \
    mail -s "Jifa Storage Alert" admin@company.com
fi
```

## 🐳 Docker部署详细配置

### 1. Docker存储目录映射

**关键发现**：Docker容器内默认使用 `/jifa-storage` 目录

#### 正确的Docker部署配置：
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  jifa:
    image: eclipsejifa/jifa:latest
    container_name: jifa-server
    ports:
      - "8102:8102"
    
    # 关键配置：将数据盘映射到容器内
    volumes:
      - /data/jifa-storage:/jifa-storage:rw
      - /data/jifa-logs:/logs:rw
    
    environment:
      - JIFA_STORAGE_PATH=/jifa-storage
      - JIFA_ROLE=STANDALONE_WORKER
      - JAVA_OPTS=-Xmx128g -Xms64g -XX:MaxMetaspaceSize=2g
    
    # 资源限制
    deploy:
      resources:
        limits:
          memory: 240G
          cpus: '70'
    
    restart: unless-stopped
    
networks:
  default:
    driver: bridge
```

### 2. Kubernetes部署配置

```yaml
# jifa-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jifa
  namespace: jifa
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jifa
  template:
    metadata:
      labels:
        app: jifa
    spec:
      containers:
      - name: jifa
        image: eclipsejifa/jifa:latest
        ports:
        - containerPort: 8102
        volumeMounts:
        - name: jifa-storage
          mountPath: /jifa-storage
        env:
        - name: JIFA_STORAGE_PATH
          value: /jifa-storage
        - name: JAVA_OPTS
          value: "-Xmx128g -Xms64g"
        resources:
          limits:
            memory: "240Gi"
            cpu: "70"
          requests:
            memory: "64Gi"
            cpu: "8"
      volumes:
      - name: jifa-storage
        persistentVolumeClaim:
          claimName: jifa-pvc
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: jifa-pvc
spec:
  accessModes:
  - ReadWriteMany
  resources:
    requests:
      storage: 1Ti
  storageClassName: fast-ssd
```

## 📊 性能监控建议

### 1. 监控指标
- **磁盘使用率**: 监控 `/data/jifa-storage` 目录
- **内存使用**: 关注JVM堆内存和元空间
- **CPU使用**: 分析任务时的CPU负载
- **网络带宽**: 文件上传下载的带宽使用

### 2. 日志配置
```yaml
# 生产环境日志配置
logging:
  level:
    org.eclipse.jifa: INFO
    org.springframework.security: WARN
  file:
    path: /data/jifa-logs
    max-size: 100MB
    max-history: 30
```

## 🔧 运维脚本示例

### 1. 启动脚本
```bash
#!/bin/bash
# /usr/local/bin/start-jifa.sh

export JIFA_STORAGE_PATH=/data/jifa-storage
export JAVA_OPTS="-Xmx128g -Xms64g -XX:MaxMetaspaceSize=2g"

cd /opt/jifa
./bin/jifa --jifa.allow-login=true \
           --jifa.allow-anonymous-access=false \
           --jifa.allow-registration=false
```

### 2. 健康检查脚本
```bash
#!/bin/bash
# /usr/local/bin/jifa-healthcheck.sh

URL="http://localhost:8102/jifa-api/health-check"
response=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

if [ "$response" -eq 200 ]; then
    echo "Jifa service is healthy"
    exit 0
else
    echo "Jifa service is unhealthy (HTTP $response)"
    exit 1
fi
```

## 💡 总结与建议

### 关键配置要点：
1. **存储路径**: 必须配置为数据盘 `/data/jifa-storage`
2. **内存分配**: 根据服务器规格合理分配JVM内存
3. **安全配置**: 禁用匿名访问，使用强密码
4. **清理策略**: 实现自动清理机制避免磁盘满
5. **监控告警**: 设置磁盘使用率监控

### 针对您的问题解答：
- **Docker存储目录**: 容器内使用 `/jifa-storage`，通过volume映射到宿主机数据盘
- **文件删除**: 当前只删除文件本身，索引文件需要额外清理
- **安全性**: 建议配置认证授权，限制内部网络访问
- **自动清理**: 需要自行实现定时清理任务

按照以上配置，您的72c256G服务器可以充分发挥性能优势，同时确保数据安全和系统稳定性。