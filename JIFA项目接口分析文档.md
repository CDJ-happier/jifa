# Eclipse Jifa 项目接口分析文档

## 项目概述

Eclipse Jifa 是一个在线分析工具，支持对以下类型的文件进行分析：
- **Heap Dump** (.hprof文件) - Java堆转储分析
- **GC Log** - GC日志分析
- **Thread Dump** - 线程转储分析
- **JFR File** - Java Flight Recorder文件分析

## 接口定义

### 1. 文件传输接口

#### HTTP API 端点
- **基础路径**: `/jifa-api`
- **文件传输**: `POST /jifa-api/files/transfer`
- **文件上传**: `POST /jifa-api/files/upload`
- **分析API**: `POST /jifa-api/analysis`

#### 文件传输请求格式
```json
{
    "type": "HEAP_DUMP",
    "method": "URL",
    "url": "https://example.com/path/to/file.hprof"
}
```

**支持的传输方法**:
- `URL`: 通过URL下载文件
- `OSS`: 阿里云OSS传输
- `S3`: AWS S3传输
- `SCP`: SSH文件传输
- `TEXT`: 文本内容传输

### 2. 分析API接口

#### 分析请求格式
```json
{
    "namespace": "heap-dump",
    "api": "getOverview",
    "target": "文件唯一标识",
    "parameters": {}
}
```

**支持的namespace**:
- `heap-dump`: 堆转储分析
- `gc-log`: GC日志分析
- `thread-dump`: 线程转储分析
- `jfr-file`: JFR文件分析

## 存储配置

### 1. 存储路径配置

**默认配置** (`application.yml`):
```yaml
jifa:
  storage-path: ${user.home}/jifa-storage
```

**存储目录结构**:
```
${storage-path}/
├── heap-dump/          # 堆转储文件
│   └── {file-id}/
│       └── {file-name}
├── gc-log/             # GC日志文件
│   └── {file-id}/
│       └── {file-name}
├── thread-dump/       # 线程转储文件
│   └── {file-id}/
│       └── {file-name}
└── jfr-file/          # JFR文件
    └── {file-id}/
        └── {file-name}
```

### 2. 数据库配置

**支持的数据库**:
- MySQL (生产环境)
- H2 (开发环境)

**配置参数**:
```yaml
jifa:
  database-host: ${MYSQL_HOST:}
  database-name: ${MYSQL_DATABASE:jifa}
  database-user: ${MYSQL_USER:jifa}
  database-password: ${MYSQL_PASSWORD:jifa}
```

## 分析工具

### 1. Heap Dump 分析工具

**底层工具**: Eclipse Memory Analyzer Tool (MAT)

**支持的功能**:
- 概览分析
- 内存泄漏检测
- GC根路径分析
- 支配树分析
- 类直方图
- 不可达对象分析
- 重复类检测
- 类加载器分析
- 直接字节缓冲区分析
- 系统属性分析
- 线程信息分析
- OQL查询

### 2. GC Log 分析工具

**支持的GC类型**:
- Serial GC
- Parallel GC
- CMS GC
- G1 GC
- ZGC

**支持的功能**:
- 基本信息分析
- 诊断分析
- 时间图表
- 暂停信息
- 堆和元空间分析
- 阶段和原因分析
- 对象统计
- JVM选项分析
- GC详情分析
- GC日志对比

### 3. Thread Dump 分析工具

**支持的功能**:
- 线程状态分析
- 死锁检测
- 线程堆栈分析
- 线程分组统计

### 4. JFR File 分析工具

**支持的功能**:
- 性能事件分析
- 内存使用分析
- CPU使用分析
- I/O操作分析
- 方法分析

## 自动清理策略

### 1. 文件清理机制

**清理方法**: `StorageService.scavenge()`

**清理逻辑**:
```java
public void scavenge(FileType type, String name) {
    Path directory = basePath.resolve(type.getStorageDirectoryName()).resolve(name);
    FileUtils.deleteQuietly(directory.toFile());
}
```

**清理时机**:
- 文件传输失败时自动清理
- 手动删除文件时调用
- 目前**没有自动定时清理机制**

### 2. 临时文件处理

**临时目录使用**: 项目**没有使用系统临时目录**，所有文件都存储在配置的存储路径中

**文件组织**: 每个文件都有自己的独立目录，便于管理和清理

## 数据盘配置建议

### 1. 修改存储路径到数据盘

**当前问题**: 默认使用 `${user.home}/jifa-storage`，可能位于系统盘

**解决方案**: 修改 `application.yml` 配置

```yaml
jifa:
  storage-path: /data/jifa-storage  # 修改为数据盘路径
```

### 2. 数据盘配置步骤

1. **创建数据目录**:
   ```bash
   sudo mkdir -p /data/jifa-storage
   sudo chown $USER:$USER /data/jifa-storage
   ```

2. **修改配置文件**:
   ```bash
   # 编辑 application.yml
   vim /path/to/jifa/server/src/main/resources/application.yml
   ```

3. **重新构建部署**:
   ```bash
   ./gradlew clean build
   ```

### 3. 存储空间监控

**API接口**:
- `GET /jifa-api/storage/space` - 获取存储空间信息

**可用方法**:
```java
long getAvailableSpace()  // 获取可用空间
long getTotalSpace()      // 获取总空间
```

## 部署配置

### 1. 运行模式

**支持的角色**:
- `standalone-worker`: 独立工作节点
- `master`: 主节点
- `static-worker`: 静态工作节点
- `elastic-worker`: 弹性工作节点

### 2. 端口配置

**默认端口**: 8102

**配置方式**:
```yaml
server:
  port: 8102
```

### 3. 安全配置

**认证机制**:
- JWT Token认证
- OAuth2客户端支持
- OAuth2资源服务器支持

**配置参数**:
```yaml
jifa:
  allow-login: false          # 是否允许登录
  allow-anonymous-access: true # 是否允许匿名访问
  allow-registration: false   # 是否允许注册
```

## 性能优化建议

### 1. 文件上传限制

**默认配置**:
```yaml
spring:
  servlet:
    multipart:
      max-request-size: 512MB
      max-file-size: 512MB
```

### 2. 线程池配置

**文件传输线程池**:
```java
executor = ExecutorFactory.newExecutor("File Transfer")
```

**调度任务线程池**:
```yaml
spring:
  task:
    scheduling:
      pool:
        size: 8
```

## 监控和维护

### 1. 健康检查

**端点**: `GET /jifa-api/health-check`

### 2. 文件管理

**获取所有文件**:
```java
Map<FileType, Set<String>> getAllFiles()
```

### 3. 存储空间监控

建议定期监控 `/data/jifa-storage` 目录的使用情况，避免磁盘空间不足。

## 总结

Eclipse Jifa 项目提供了完整的文件分析和存储解决方案：

1. **接口设计**: RESTful API设计，支持多种文件传输方式
2. **分析工具**: 基于成熟的工具（Eclipse MAT等）进行深度分析
3. **存储管理**: 文件按类型和ID组织，便于管理和清理
4. **配置灵活**: 支持数据盘存储，避免系统盘空间压力
5. **扩展性强**: 模块化设计，支持多种部署模式

**关键改进点**:
- 将存储路径从默认的用户主目录迁移到数据盘
- 考虑实现自动清理机制，避免长期运行导致的磁盘空间问题
- 加强存储空间监控和告警机制