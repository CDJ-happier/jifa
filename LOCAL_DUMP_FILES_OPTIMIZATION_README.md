# Jifa 本地 Dump 文件自动加载功能优化说明

## 更新日期：2026-02-05

## 功能概述

已经实现了三个重要的优化功能：

### 1. 使用符号链接代替文件复制 ✅
- **问题**：之前使用 `Files.copy()` 复制文件，导致重复占用磁盘空间
- **解决方案**：使用符号链接（`Files.createSymbolicLink()`），不占用额外空间
- **配置项**：`use-symbolic-link-for-local-files: true` （默认启用）

### 2. 支持 .gz 压缩的 Heap Dump 文件 ✅
- **问题**：只支持未压缩的 .hprof 文件
- **解决方案**：自动检测并解压 `.hprof.gz` 文件
- **实现**：
  - 检测文件扩展名 `.hprof.gz`
  - 自动使用 GZIPInputStream 解压
  - 解压后的文件用于分析
  - 如果使用符号链接模式，保留临时解压文件；否则删除

### 3. 定期扫描新文件 ✅
- **问题**：启动后新添加的文件不会被自动识别
- **解决方案**：实现了定期扫描机制
- **配置项**：`local-dump-files-scan-interval: 300` （默认5分钟）
- **功能**：
  - 启动后立即扫描一次
  - 每隔指定时间自动扫描
  - 设置为 0 则只在启动时扫描一次

### 4. 避免重复加载 ✅
- **问题**：同一个文件多次出现在列表中
- **解决方案**：添加了重复检查逻辑
- **实现**：在加载文件前检查数据库中是否已存在同名同类型的文件

## 配置说明

### 生产环境配置 `/data/jifa/config/application.yml`

```yaml
jifa:
  role: standalone-worker
  storage-path: /data/jifa/storage

  # 本地dump文件目录（启动时自动扫描并加载）
  local-dump-files-directory: /data/dump_files

  # 使用符号链接代替复制文件（节省磁盘空间）
  use-symbolic-link-for-local-files: true

  # 扫描间隔（秒），0表示仅启动时扫描，默认300秒=5分钟
  local-dump-files-scan-interval: 300
```

### 配置项详解

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `local-dump-files-directory` | Path | null | 本地dump文件目录路径 |
| `use-symbolic-link-for-local-files` | boolean | true | 是否使用符号链接而不是复制文件 |
| `local-dump-files-scan-interval` | int | 300 | 扫描间隔（秒），0=仅启动时扫描 |

## 支持的文件格式

### Heap Dump 文件
- `.hprof` - 标准 Java Heap Dump
- `.hprof.gz` - 压缩的 Heap Dump（自动解压）✨ 新增
- `.bin` - 二进制 dump 文件

### 其他文件类型
- `.log` - GC 日志文件
- `.txt` - 线程 dump 文件

## 工作流程

### 启动时
1. Jifa 服务启动
2. `ReadyListener` 触发 `LocalDumpFilesScanner.scanDirectory()`
3. 扫描 `/data/dump_files` 目录（仅第一层，不递归）
4. 对每个支持的文件：
   - 检查是否已加载（避免重复）
   - 如果是 `.hprof.gz`，自动解压
   - 使用 `AnalysisApiService.deduceFileType()` 识别文件类型
   - 根据配置使用符号链接或复制文件
   - 保存文件信息到数据库
   - 记录文件访问URL到日志

### 定期扫描
1. 启动10秒后开始第一次定期扫描
2. 之后每隔 `local-dump-files-scan-interval` 秒扫描一次
3. 扫描逻辑与启动时相同
4. 使用 `@Scheduled` 注解实现

## 核心代码文件

### 1. LocalDumpFilesScanner.java（新增）
```
/opt/jifa/server/src/main/java/org/eclipse/jifa/server/service/LocalDumpFilesScanner.java
```

主要职责：
- 实现目录扫描逻辑
- 处理 .gz 文件解压
- 重复文件检测
- 定期扫描任务

### 2. Configuration.java（修改）
添加配置项：
- `localDumpFilesDirectory`
- `useSymbolicLinkForLocalFiles`
- `localDumpFilesScanInterval`

### 3. StorageService.java & StorageServiceImpl.java（修改）
添加方法：
- `handleLocalFileWithSymlink()` - 使用符号链接

### 4. FileService.java & FileServiceImpl.java（修改）
添加方法：
- `handleLocalFileRequest(type, path, useSymlink)` - 支持符号链接参数
- `isFileAlreadyLoaded(originalName, type)` - 检查文件是否已加载

### 5. ReadyListener.java（修改）
- 注入 `LocalDumpFilesScanner`
- 使用扫描服务代替原有的简单扫描逻辑

## 使用示例

### 场景1：添加新的 Heap Dump 文件

```bash
# 1. 将文件复制到监控目录
sudo cp /path/to/new/dump.hprof /data/dump_files/

# 2. 确保文件权限正确
sudo chmod 644 /data/dump_files/dump.hprof

# 3. 等待定期扫描（默认5分钟），或重启服务立即扫描
sudo systemctl restart jifa

# 4. 查看日志确认
sudo journalctl -u jifa -f | grep "Scanning"
```

### 场景2：添加压缩的 Heap Dump 文件

```bash
# 1. 将压缩文件复制到监控目录
sudo cp /path/to/dump.hprof.gz /data/dump_files/

# 2. 文件会被自动解压并分析
# 查看日志
sudo journalctl -u jifa -f | grep "Decompressing"
```

### 场景3：调整扫描频率

```yaml
# 修改配置文件
# 每分钟扫描一次
local-dump-files-scan-interval: 60

# 或者禁用定期扫描，仅启动时扫描
local-dump-files-scan-interval: 0
```

## 日志示例

### 正常启动扫描
```
2026-02-05T11:30:11.003+08:00  INFO --- Jifa Server: http://localhost:8080
2026-02-05T11:30:11.003+08:00  INFO --- Scanning local dump files directory: /data/dump_files
2026-02-05T11:30:11.012+08:00  DEBUG --- File already loaded, skipping: jj.hprof
```

### .gz 文件处理
```
2026-02-05T11:30:15.120+08:00  INFO --- Decompressing .gz file: dump.hprof.gz
2026-02-05T11:30:45.300+08:00  INFO --- dump.hprof: http://localhost:8080/heap-dump-analysis/xxx
```

### 定期扫描
```
2026-02-05T11:35:11.003+08:00  INFO --- Scanning local dump files directory: /data/dump_files
```

## 性能和资源考虑

### 磁盘空间
- **使用符号链接**：不占用额外空间
- **复制文件模式**：需要双倍空间（原文件 + 副本）
- **推荐**：启用符号链接模式

### 内存占用
- 扫描过程：占用少量内存
- .gz 解压：需要临时内存（buffer 8KB）
- 对大文件：解压过程分块进行，不会一次性加载到内存

### CPU 使用
- 扫描：CPU使用很低
- .gz 解压：CPU密集型操作，建议在空闲时段进行
- 定期扫描：使用后台线程，不影响前端请求

## 故障排查

### 问题1：文件没有被扫描到

**检查清单**：
1. 文件权限：确保 jifa 用户可读
   ```bash
   sudo chmod 644 /data/dump_files/*.hprof
   ```

2. 文件格式：确保是支持的格式
   ```bash
   file /data/dump_files/your-file.hprof
   ```

3. 查看日志：
   ```bash
   sudo journalctl -u jifa -f | grep -E "(Scanning|Failed)"
   ```

### 问题2：.gz 文件解压失败

**可能原因**：
- 文件损坏或不完整
- 不是有效的 gzip 格式

**解决方法**：
```bash
# 验证 gz 文件完整性
gunzip -t /data/dump_files/file.hprof.gz

# 手动解压测试
gunzip -c /data/dump_files/file.hprof.gz > /tmp/test.hprof
```

### 问题3：文件重复出现

**原因**：旧版本创建的重复记录

**解决方法**：
1. 在前端删除重复的文件记录
2. 或者清理数据库后重启服务

### 问题4：定期扫描不工作

**检查配置**：
```bash
# 查看配置
cat /data/jifa/config/application.yml | grep scan-interval

# 确保不是 0（0 表示禁用定期扫描）
```

**查看日志**：
```bash
# 应该每隔配置的时间看到扫描日志
sudo journalctl -u jifa -f | grep "Scanning"
```

## 限制和注意事项

1. **符号链接限制**：
   - 原文件不能移动或删除
   - 如果原文件被删除，分析会失败
   - 建议 `/data/dump_files` 作为永久存储目录

2. **.gz 文件处理**：
   - 仅支持 `.hprof.gz` 格式的 Heap Dump
   - GC 日志的 .gz 文件暂不支持自动解压
   - 解压后的临时文件可能占用临时空间

3. **扫描频率**：
   - 扫描间隔太短会增加 CPU 负担
   - 建议最小间隔 60 秒
   - 默认 300 秒（5 分钟）是推荐值

4. **并发扫描**：
   - 同时只能有一个扫描任务运行
   - 如果上次扫描未完成，新的扫描会被跳过

## 升级说明

### 从旧版本升级

1. 旧数据不受影响，继续可用
2. 新配置项有默认值，无需修改也能工作
3. 建议添加配置以启用所有新功能
4. 重启服务后立即生效

### 回滚方案

如果遇到问题需要回滚：
1. 停止服务：`sudo systemctl stop jifa`
2. 恢复旧版本应用
3. 删除新增的配置项
4. 启动服务：`sudo systemctl start jifa`

## API 接口

文件列表接口保持不变：
```bash
# 查看所有文件
curl http://localhost:8080/jifa-api/files?page=1&pageSize=20

# 查看特定类型
curl http://localhost:8080/jifa-api/files?type=HEAP_DUMP&page=1&pageSize=20
```

## 总结

本次优化解决了三个主要问题：

1. ✅ **磁盘空间问题**：使用符号链接避免文件重复
2. ✅ **压缩文件支持**：自动处理 .hprof.gz 文件
3. ✅ **实时性问题**：定期扫描自动发现新文件
4. ✅ **重复加载问题**：检查避免同一文件多次加载

所有功能都已实现并在生产环境中验证，配置灵活，可根据实际需求调整。

---

**版本**：Jifa 0.3.0-SNAPSHOT
**状态**：✅ 已实现并部署
**部署时间**：2026-02-05 11:32
