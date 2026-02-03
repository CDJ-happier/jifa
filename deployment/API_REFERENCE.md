# Jifa Heap Dump API 完整文档

## 概述

Jifa 提供完整的 REST API 用于 heap dump 文件上传、分析和查询。

## 基础信息

- **Base URL**: `http://localhost:8080/jifa-api`
- **Content-Type**: `application/json`

## API 流程图

```
1. 上传文件 (URL 方式)
   POST /files/transfer
   ↓
2. 查询上传进度
   GET /files/transfer/{transferId}
   ↓
3. 获取文件信息
   GET /files?type=HEAP_DUMP&page=1&pageSize=25
   ↓
4. 触发分析
   POST /analysis
   {"namespace":"heap-dump","api":"analyze",...}
   ↓
5. 查询分析进度
   POST /analysis
   {"namespace":"heap-dump","api":"progressOfAnalysis",...}
   ↓
6. 获取分析结果
   POST /analysis
   {"namespace":"heap-dump","api":"getDetails",...}
```

---

## 1. 文件管理 API

### 1.1 上传文件（URL 方式）

从指定 URL 下载并上传文件到 Jifa。

**请求:**
```bash
POST /files/transfer
Content-Type: application/json

{
  "type": "HEAP_DUMP",
  "method": "URL",
  "url": "https://example.com/dump.hprof"
}
```

**响应:**
```
2
```
返回 `transferId`（纯数字）。

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/files/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "type": "HEAP_DUMP",
    "method": "URL",
    "url": "https://example.com/dump.hprof"
  }'
```

---

### 1.2 查询上传进度

**请求:**
```bash
GET /files/transfer/{transferId}
```

**响应（上传中）:**
```json
{
  "state": "IN_PROGRESS",
  "totalSize": 393046228,
  "transferredSize": 162321079
}
```

**响应（上传完成）:**
```json
{
  "state": "SUCCESS",
  "totalSize": 393046228,
  "transferredSize": 393046228,
  "fileId": 1
}
```

**状态说明:**
- `IN_PROGRESS`: 上传中
- `SUCCESS`: 上传成功
- `FAILED`: 上传失败

**示例:**
```bash
curl http://localhost:8080/jifa-api/files/transfer/2
```

---

### 1.3 查询文件列表

**请求:**
```bash
GET /files?type=HEAP_DUMP&page=1&pageSize=25
```

**响应:**
```json
{
  "data": [
    {
      "id": 1,
      "uniqueName": "497dda82-542e-416c-8d5c-352eb252dbbe",
      "originalName": "dump_jasondjcai_1769754421863.hprof",
      "type": "HEAP_DUMP",
      "size": 393046228,
      "createdTime": "2026-02-03 14:43:44"
    }
  ],
  "page": 1,
  "pageSize": 25,
  "totalSize": 1
}
```

**参数说明:**
- `type`: 文件类型（HEAP_DUMP, GC_LOG, THREAD_DUMP, JFR_FILE）
- `page`: 页码（从 1 开始）
- `pageSize`: 每页大小

**示例:**
```bash
curl -G http://localhost:8080/jifa-api/files \
  --data-urlencode "type=HEAP_DUMP" \
  --data-urlencode "page=1" \
  --data-urlencode "pageSize=25"
```

⚠️ **注意**: 必须使用 `-G --data-urlencode` 或手动转义 URL 参数，否则 shell 会误解析 `&` 符号。

---

### 1.4 上传文件（multipart 方式）

直接上传本地文件。

**请求:**
```bash
POST /files/upload?type=HEAP_DUMP
Content-Type: multipart/form-data

file: <binary file data>
```

**响应:**
```
1
```
返回 `fileId`（纯数字）。

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/files/upload \
  -F "type=HEAP_DUMP" \
  -F "file=@dump.hprof"
```

---

## 2. 分析 API

所有分析 API 使用统一的请求格式：

```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "<api-method-name>",
  "target": "<file-unique-name>",
  "parameters": { ... }
}
```

**字段说明:**
- `namespace`: 固定为 `"heap-dump"`
- `api`: API 方法名（见下文）
- `target`: 文件的 `uniqueName`（从文件列表获取）
- `parameters`: API 方法的参数（可选）

---

### 2.1 触发分析

开始分析 heap dump 文件。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "analyze",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
  "parameters": {}
}
```

**响应:**
```json
{
  "state": "IN_PROGRESS",
  "percent": 0.0,
  "message": "Starting analysis..."
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "analyze",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {}
  }'
```

---

### 2.2 查询分析进度

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "progressOfAnalysis",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe"
}
```

**响应（分析中）:**
```json
{
  "state": "IN_PROGRESS",
  "percent": 0.35,
  "message": "Building dominator tree..."
}
```

**响应（分析完成）:**
```json
{
  "state": "SUCCESS",
  "percent": 1.0,
  "message": "Analysis completed"
}
```

**状态说明:**
- `IN_PROGRESS`: 分析中
- `SUCCESS`: 分析成功
- `FAILURE`: 分析失败

**percent 范围**: `0.0` - `1.0`（0% - 100%）

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "progressOfAnalysis",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe"
  }'
```

---

### 2.3 获取概览信息

获取 heap dump 的基本信息和统计数据。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getDetails",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe"
}
```

**响应示例:**
```json
{
  "heapSize": 393046228,
  "objectCount": 1234567,
  "classCount": 5678,
  "gcRootCount": 234,
  "creationDate": "2026-02-03 14:43:44",
  "identifierSize": 8,
  "jvmInfo": "OpenJDK 64-Bit Server VM (17.0.8+7)",
  "systemProperties": { ... }
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getDetails",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe"
  }'
```

---

### 2.4 获取最大对象

获取占用内存最多的对象列表。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getBiggestObjects",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
  "parameters": {
    "page": 1,
    "pageSize": 50
  }
}
```

**响应示例:**
```json
{
  "data": [
    {
      "objectId": 12345,
      "label": "byte[] @ 0x7f8a9c000000",
      "shallowSize": 104857600,
      "retainedSize": 104857600,
      "type": "byte[]"
    },
    ...
  ],
  "page": 1,
  "pageSize": 50,
  "totalSize": 234
}
```

**字段说明:**
- `shallowSize`: 对象自身占用的内存
- `retainedSize`: 对象及其引用树占用的总内存
- `objectId`: 对象 ID（用于进一步查询）

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getBiggestObjects",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

### 2.5 获取内存泄漏报告

自动检测潜在的内存泄漏问题。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getLeakReport",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe"
}
```

**响应示例:**
```json
{
  "suspects": [
    {
      "objectId": 12345,
      "className": "java.util.HashMap",
      "retainedSize": 104857600,
      "suspectReason": "占用 25% 的堆内存",
      "description": "HashMap containing 100,000 entries"
    },
    ...
  ]
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getLeakReport",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe"
  }'
```

---

### 2.6 获取直方图（Histogram）

按类分组统计对象数量和内存占用。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getHistogram",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
  "parameters": {
    "groupBy": "BY_CLASS",
    "page": 1,
    "pageSize": 100,
    "sortBy": "RETAINED_SIZE",
    "ascendingOrder": false
  }
}
```

**参数说明:**
- `groupBy`: 分组方式
  - `BY_CLASS`: 按类名分组
  - `BY_PACKAGE`: 按包名分组
  - `BY_CLASSLOADER`: 按类加载器分组
  - `BY_SUPERCLASS`: 按父类分组
- `sortBy`: 排序字段
  - `SHALLOW_SIZE`: 按浅层大小
  - `RETAINED_SIZE`: 按保留大小
  - `OBJECTS`: 按对象数量
- `ascendingOrder`: 是否升序（false = 降序）

**响应示例:**
```json
{
  "data": [
    {
      "label": "byte[]",
      "objects": 45678,
      "shallowSize": 234567890,
      "retainedSize": 234567890
    },
    {
      "label": "java.lang.String",
      "objects": 123456,
      "shallowSize": 12345678,
      "retainedSize": 23456789
    },
    ...
  ],
  "page": 1,
  "pageSize": 100,
  "totalSize": 5678
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getHistogram",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "groupBy": "BY_CLASS",
      "page": 1,
      "pageSize": 100,
      "sortBy": "RETAINED_SIZE",
      "ascendingOrder": false
    }
  }'
```

---

### 2.7 获取支配树（Dominator Tree）

获取支配树视图，显示对象之间的支配关系。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getDominatorTree",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
  "parameters": {
    "page": 1,
    "pageSize": 50,
    "sortBy": "RETAINED_SIZE",
    "ascendingOrder": false
  }
}
```

**响应示例:**
```json
{
  "data": [
    {
      "objectId": 12345,
      "label": "java.lang.Thread @ 0x7f8a9c000000",
      "shallowSize": 112,
      "retainedSize": 104857600,
      "hasChildren": true
    },
    ...
  ],
  "page": 1,
  "pageSize": 50,
  "totalSize": 234
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getDominatorTree",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "page": 1,
      "pageSize": 50,
      "sortBy": "RETAINED_SIZE",
      "ascendingOrder": false
    }
  }'
```

---

### 2.8 获取 GC Roots 路径

查找对象到 GC Roots 的引用路径。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getPathToGCRoots",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
  "parameters": {
    "objectId": 12345,
    "skip": 0,
    "count": 10
  }
}
```

**参数说明:**
- `objectId`: 目标对象 ID
- `skip`: 跳过前 N 条路径
- `count`: 返回路径数量

**响应示例:**
```json
{
  "paths": [
    {
      "objects": [
        {
          "objectId": 1,
          "label": "System Class",
          "type": "GC_ROOT"
        },
        {
          "objectId": 100,
          "label": "java.lang.Thread @ 0x..."
        },
        {
          "objectId": 12345,
          "label": "java.util.HashMap @ 0x..."
        }
      ]
    },
    ...
  ]
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getPathToGCRoots",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "objectId": 12345,
      "skip": 0,
      "count": 10
    }
  }'
```

---

### 2.9 获取线程信息

获取 heap dump 中的线程信息。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getThreads",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
  "parameters": {
    "page": 1,
    "pageSize": 50
  }
}
```

**响应示例:**
```json
{
  "data": [
    {
      "objectId": 12345,
      "name": "main",
      "shallowSize": 112,
      "retainedSize": 104857600,
      "contextClassLoader": "sun.misc.Launcher$AppClassLoader @ 0x...",
      "isDaemon": false
    },
    {
      "objectId": 12346,
      "name": "GC Thread#0",
      "shallowSize": 80,
      "retainedSize": 1024,
      "isDaemon": true
    },
    ...
  ],
  "page": 1,
  "pageSize": 50,
  "totalSize": 123
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getThreads",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

### 2.10 执行 OQL 查询

使用 Object Query Language 执行复杂查询。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getOQLResult",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
  "parameters": {
    "oql": "select * from java.lang.String s where s.value.length > 1000",
    "page": 1,
    "pageSize": 50
  }
}
```

**OQL 示例:**
```sql
-- 查找所有 String 对象
select * from java.lang.String

-- 查找长度超过 1000 的 String
select * from java.lang.String s where s.value.length > 1000

-- 查找所有 HashMap 及其大小
select s, s.size from java.util.HashMap s

-- 查找内存占用超过 1MB 的对象
select * from instanceof java.lang.Object s where sizeof(s) > 1048576
```

**响应示例:**
```json
{
  "data": [
    {
      "objectId": 12345,
      "label": "java.lang.String @ 0x...",
      "value": "very long string content..."
    },
    ...
  ],
  "page": 1,
  "pageSize": 50,
  "totalSize": 234
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getOQLResult",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "oql": "select * from java.lang.String s where s.value.length > 1000",
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

### 2.11 执行 SQL 查询

使用 Calcite SQL 执行查询（更强大的查询能力）。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getCalciteSQLResult",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
  "parameters": {
    "sql": "SELECT className, COUNT(*) as count, SUM(shallowSize) as totalSize FROM Objects GROUP BY className ORDER BY totalSize DESC LIMIT 10",
    "page": 1,
    "pageSize": 50
  }
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getCalciteSQLResult",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "sql": "SELECT className, COUNT(*) as count, SUM(shallowSize) as totalSize FROM Objects GROUP BY className ORDER BY totalSize DESC LIMIT 10",
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

### 2.12 获取对象详情

获取特定对象的详细信息。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getObjectInfo",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
  "parameters": {
    "objectId": 12345
  }
}
```

**响应示例:**
```json
{
  "objectId": 12345,
  "address": "0x7f8a9c000000",
  "className": "java.util.HashMap",
  "classId": 5678,
  "shallowSize": 48,
  "retainedSize": 104857600,
  "gcRootInfo": null
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getObjectInfo",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "objectId": 12345
    }
  }'
```

---

### 2.13 获取对象字段

获取对象的所有字段和值。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getFields",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
  "parameters": {
    "objectId": 12345,
    "page": 1,
    "pageSize": 50
  }
}
```

**响应示例:**
```json
{
  "data": [
    {
      "name": "size",
      "type": "int",
      "value": "1024"
    },
    {
      "name": "table",
      "type": "java.util.HashMap$Node[]",
      "value": "java.util.HashMap$Node[16] @ 0x...",
      "objectId": 12346
    },
    ...
  ],
  "page": 1,
  "pageSize": 50,
  "totalSize": 12
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getFields",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "objectId": 12345,
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

### 2.14 获取 Inspector 视图

获取对象的详细视图，包括字段、出入边等。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "getInspectorView",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
  "parameters": {
    "objectId": 12345
  }
}
```

**响应示例:**
```json
{
  "objectInfo": {
    "objectId": 12345,
    "className": "java.util.HashMap",
    "shallowSize": 48,
    "retainedSize": 104857600
  },
  "fields": [...],
  "staticFields": [...],
  "outbounds": [...],
  "inbounds": [...]
}
```

**示例:**
```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getInspectorView",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "objectId": 12345
    }
  }'
```

---

## 3. 实用工具方法

### 3.1 检查是否需要分析选项

在触发分析前检查是否需要额外的分析选项。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "needOptionsForAnalysis",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe"
}
```

**响应:**
```json
{
  "needed": false
}
```

---

### 3.2 释放分析器

释放内存中的分析器实例。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "release",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe"
}
```

---

### 3.3 清理分析结果

清理磁盘上的分析缓存和索引文件。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "clean",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe"
}
```

---

### 3.4 获取错误日志

获取分析过程中的错误日志。

**请求:**
```bash
POST /analysis
Content-Type: application/json

{
  "namespace": "heap-dump",
  "api": "errorLog",
  "target": "497dda82-542e-416c-8d5c-352eb252dbbe"
}
```

**响应示例:**
```json
{
  "logs": [
    "2026-02-03 14:45:23 [WARN] Object 12345 has broken reference",
    "2026-02-03 14:45:30 [ERROR] Failed to parse object 56789"
  ]
}
```

---

## 4. Web UI 访问

分析完成后，可以通过浏览器访问 Web UI：

```
http://{JIFA_HOST}:{JIFA_PORT}/#/heap/{uniqueName}
```

例如：
```
http://21.6.180.85:8080/#/heap/497dda82-542e-416c-8d5c-352eb252dbbe
```

---

## 5. 错误处理

所有 API 在出错时返回统一的错误格式：

```json
{
  "errorCode": "ERROR_CODE_NAME",
  "message": "Detailed error message"
}
```

**常见错误码:**
- `ILLEGAL_ARGUMENT`: 参数错误
- `FILE_NOT_FOUND`: 文件不存在
- `INTERNAL_ERROR`: 内部错误
- `ANALYSIS_FAILED`: 分析失败

---

## 6. 完整示例脚本

参考 `/opt/jifa/scripts/auto-analyze-heap-dump.sh`，该脚本实现了完整的自动化流程：

```bash
bash /opt/jifa/scripts/auto-analyze-heap-dump.sh \
  "https://example.com/dump.hprof"
```

---

## 7. 性能建议

1. **大文件上传**:
   - 对于超大文件（>10GB），建议使用 URL 方式而非 multipart 上传
   - 确保网络带宽充足

2. **分析性能**:
   - 分析时间与文件大小成正比
   - 128GB 服务器配置建议 JVM 堆内存 180GB
   - 分析期间服务器负载较高，避免并发分析多个文件

3. **内存管理**:
   - 分析完成后建议调用 `release` API 释放内存
   - 长期不使用的文件可调用 `clean` API 清理缓存

---

## 8. 附录：API 方法速查表

| API 方法 | 用途 | 参数 |
|---------|------|------|
| `analyze` | 触发分析 | - |
| `progressOfAnalysis` | 查询分析进度 | - |
| `getDetails` | 获取概览信息 | - |
| `getBiggestObjects` | 获取最大对象 | page, pageSize |
| `getLeakReport` | 获取泄漏报告 | - |
| `getHistogram` | 获取直方图 | groupBy, page, pageSize, sortBy |
| `getDominatorTree` | 获取支配树 | page, pageSize, sortBy |
| `getPathToGCRoots` | 获取 GC Roots 路径 | objectId, skip, count |
| `getThreads` | 获取线程信息 | page, pageSize |
| `getOQLResult` | 执行 OQL 查询 | oql, page, pageSize |
| `getCalciteSQLResult` | 执行 SQL 查询 | sql, page, pageSize |
| `getObjectInfo` | 获取对象详情 | objectId |
| `getFields` | 获取对象字段 | objectId, page, pageSize |
| `getInspectorView` | 获取 Inspector 视图 | objectId |
| `release` | 释放分析器 | - |
| `clean` | 清理缓存 | - |
| `errorLog` | 获取错误日志 | - |

---

**版本**: 1.0
**更新时间**: 2026-02-03
**Jifa 版本**: 0.3.0-SNAPSHOT
