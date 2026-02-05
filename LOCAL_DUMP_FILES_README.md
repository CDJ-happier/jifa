# Jifa 本地 Dump 文件自动加载功能

## 功能说明

Jifa 现已支持在启动时自动扫描并加载指定目录下的 dump 文件，无需手动上传即可在前端界面查看和分析这些文件。

## 配置方法

在配置文件中添加 `local-dump-files-directory` 配置项：

### 方式一：修改 application.yml

```yaml
jifa:
  role: standalone-worker
  storage-path: /data/jifa/storage
  local-dump-files-directory: /data/dump_files  # 添加此配置
```

### 方式二：通过启动参数

```bash
java -jar jifa.jar --jifa.local-dump-files-directory=/data/dump_files
```

### 方式三：通过环境变量

```bash
export JIFA_LOCAL_DUMP_FILES_DIRECTORY=/data/dump_files
java -jar jifa.jar
```

## 支持的文件类型

系统会自动扫描目录下的以下文件（仅扫描目录第一层，不递归子目录）：

- `.hprof` - Heap Dump 文件
- `.bin` - 二进制 dump 文件
- `.log` - GC 日志文件
- `.txt` - 线程 dump 文件

## 工作原理

1. **启动扫描**：Jifa 启动时，如果配置了 `local-dump-files-directory`，会自动扫描该目录
2. **类型识别**：系统会自动识别文件类型（Heap Dump、GC Log、Thread Dump）
3. **文件复制**：扫描到的文件会被复制到 Jifa 存储目录（`storage-path`）
4. **数据库记录**：文件信息会保存到数据库中
5. **前端展示**：文件会出现在前端的文件列表中，可以直接点击分析

## 实际效果验证

### 配置示例

生产环境配置文件 `/data/jifa/config/application.yml`：

```yaml
jifa:
  role: standalone-worker
  storage-path: /data/jifa/storage
  local-dump-files-directory: /data/dump_files
```

### 启动日志

```
2026-02-05T10:50:58.334+08:00  INFO  --- Jifa Server: http://localhost:8080
2026-02-05T10:50:58.335+08:00  INFO  --- Scanning local dump files directory: /data/dump_files
2026-02-05T10:53:42.260+08:00  INFO  --- jj.hprof: http://localhost:8080/heap-dump-analysis/5c5eef81-11d6-43a2-9007-f13431d3eae6
```

### API 验证

查询文件列表：
```bash
curl http://localhost:8080/jifa-api/files?page=1&pageSize=10
```

返回结果：
```json
{
  "data": [
    {
      "id": 20,
      "uniqueName": "5c5eef81-11d6-43a2-9007-f13431d3eae6",
      "originalName": "jj.hprof",
      "type": "HEAP_DUMP",
      "size": 43262206889,
      "createdTime": "2026-02-05 10:53:42"
    }
  ]
}
```

### 前端访问

已加载的文件可以通过以下方式访问：
- 文件列表页面：`http://localhost:8080/`
- 直接分析链接：`http://localhost:8080/heap-dump-analysis/5c5eef81-11d6-43a2-9007-f13431d3eae6`

## 注意事项

1. **文件权限**：确保 Jifa 运行用户（通常是 `jifa`）对扫描目录有读取权限
2. **磁盘空间**：文件会被复制到存储目录，需要确保有足够的磁盘空间
3. **重复加载**：已加载过的文件不会重复添加（基于文件名判断）
4. **首次启动**：仅在应用启动时扫描一次，运行中新增的文件需要重启应用才能加载
5. **大文件处理**：支持处理超大文件（已验证 43GB 文件可正常加载）

## 代码修改记录

本功能涉及以下文件修改：

1. **Configuration.java** - 添加 `localDumpFilesDirectory` 配置属性
2. **ReadyListener.java** - 实现目录扫描和文件自动加载逻辑
3. **application.yml** - 添加默认配置示例

## 适用场景

这个功能特别适合以下场景：

1. **批量分析**：需要分析大量本地 dump 文件
2. **持久化存储**：dump 文件保存在独立目录，Jifa 升级重启后自动重新加载
3. **自动化运维**：脚本自动收集 dump 文件到指定目录，Jifa 自动识别和加载
4. **大文件处理**：避免通过网络上传超大文件，直接本地加载

## 示例部署流程

```bash
# 1. 创建 dump 文件目录
sudo mkdir -p /data/dump_files
sudo chmod 755 /data/dump_files

# 2. 将 dump 文件放入目录
sudo cp /path/to/your/dump.hprof /data/dump_files/

# 3. 修改配置文件
sudo vim /data/jifa/config/application.yml
# 添加：local-dump-files-directory: /data/dump_files

# 4. 重启 Jifa 服务
sudo systemctl restart jifa

# 5. 查看日志确认
sudo journalctl -u jifa -f | grep "Scanning"

# 6. 访问前端查看文件列表
# 浏览器打开：http://your-server:8080
```

## 技术实现

核心实现在 `ReadyListener.java` 的 `fireReadyEvent()` 方法中：

```java
Path dumpFilesDir = config.getLocalDumpFilesDirectory();
if (dumpFilesDir != null && Files.exists(dumpFilesDir) && Files.isDirectory(dumpFilesDir)) {
    log.info("Scanning local dump files directory: {}", dumpFilesDir);
    try (Stream<Path> files = Files.walk(dumpFilesDir, 1)) {
        files.filter(Files::isRegularFile)
             .filter(p -> {
                 String name = p.getFileName().toString().toLowerCase();
                 return name.endsWith(".hprof") || name.endsWith(".bin") ||
                        name.endsWith(".log") || name.endsWith(".txt");
             })
             .forEach(this::handleInputFile);
    }
}
```

每个文件的处理逻辑：

```java
private void handleInputFile(Path path) {
    FileType type = analysisApiService.deduceFileType(path);
    if (type != null) {
        String uniqueName = fileService.handleLocalFileRequest(type, path);
        log.info("{}: http://{}:{}/{}/{}",
                 path.getFileName(),
                 "localhost",
                 config.getPort(),
                 type.getAnalysisUrlPath(),
                 uniqueName);
    }
}
```

---

**更新时间**：2026-02-05
**版本**：Jifa 0.3.0-SNAPSHOT
**状态**：✅ 已实现并验证
