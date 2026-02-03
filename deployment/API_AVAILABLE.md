# Jifa Heap Dump 可用 API 速查表

基于实际测试，以下是**确认可用**的 API 方法。

## Base URL
```
http://localhost:8080/jifa-api/analysis
```

## 请求格式
```json
{
  "namespace": "heap-dump",
  "api": "<api-name>",
  "target": "<file-unique-name>",
  "parameters": { ... }
}
```

---

## ✅ 已验证可用的 API

### 1. 获取泄漏报告
**API**: `leak.report`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "leak.report",
    "target": "YOUR_UNIQUE_NAME"
  }'
```

**响应示例**:
```json
{
  "useful": true,
  "name": "Leak Hunter",
  "slices": [
    {
      "label": "Problem Suspect 1",
      "objectId": 1683083,
      "value": 39492968,
      "desc": "..."
    }
  ],
  "records": [...]
}
```

---

### 2. 获取线程摘要
**API**: `threadsSummary`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "threadsSummary",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "searchText": "",
      "searchType": "BY_NAME"
    }
  }'
```

---

### 3. 获取直方图（Histogram）
**API**: `getHistogram`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getHistogram",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "groupBy": "BY_CLASS",
      "ids": [],
      "sortBy": "retainedSize",
      "ascendingOrder": false,
      "searchText": "",
      "searchType": "BY_NAME",
      "page": 1,
      "pageSize": 50
    }
  }'
```

**参数说明**:
- `groupBy`: `BY_CLASS` | `BY_PACKAGE` | `BY_CLASSLOADER` | `BY_SUPERCLASS`
- `sortBy`: `retainedSize` | `shallowSize` | `objects`
- `searchType`: `BY_NAME` | `BY_PATTERN`

---

### 4. 获取支配树根节点
**API**: `dominatorTree.roots`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "dominatorTree.roots",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "groupBy": "NONE",
      "sortBy": "retainedSize",
      "ascendingOrder": false,
      "searchText": "",
      "searchType": "BY_NAME",
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

### 5. 获取支配树子节点
**API**: `dominatorTree.children`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "dominatorTree.children",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "groupBy": "NONE",
      "sortBy": "retainedSize",
      "ascendingOrder": false,
      "parentObjectId": 123456,
      "idPathInResultTree": [],
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

### 6. 获取对象信息
**API**: `object`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "object",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "objectId": 123456
    }
  }'
```

---

### 7. 获取对象详细视图
**API**: `inspector.objectView`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "inspector.objectView",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "objectId": 123456
    }
  }'
```

---

### 8. 获取对象字段
**API**: `inspector.fields`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "inspector.fields",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "objectId": 123456,
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

### 9. 获取静态字段
**API**: `inspector.staticFields`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "inspector.staticFields",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "objectId": 123456,
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

### 10. OQL 查询
**API**: `oql`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "oql",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "oql": "select * from java.lang.String",
      "sortBy": "",
      "ascendingOrder": false,
      "page": 1,
      "pageSize": 50
    }
  }'
```

**OQL 示例**:
```sql
-- 查找所有 String
select * from java.lang.String

-- 查找长字符串
select * from java.lang.String s where s.value.length > 1000

-- 查找 HashMap 及其大小
select s, s.size from java.util.HashMap s
```

---

### 11. SQL 查询
**API**: `sql`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "sql",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "sql": "SELECT className, COUNT(*) as count FROM Objects GROUP BY className ORDER BY count DESC LIMIT 10",
      "sortBy": "",
      "ascendingOrder": false,
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

### 12. 查找字符串
**API**: `findStrings`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "findStrings",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "pattern": "password",
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

### 13. 获取 GC Roots
**API**: `getGCRoots`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getGCRoots",
    "target": "YOUR_UNIQUE_NAME"
  }'
```

---

### 14. 获取路径到 GC Roots
**API**: `getPathToGCRoots`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getPathToGCRoots",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "objectId": 123456,
      "skip": 0,
      "count": 10
    }
  }'
```

---

### 15. 获取类加载器摘要
**API**: `classLoaderExplorer.summary`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "classLoaderExplorer.summary",
    "target": "YOUR_UNIQUE_NAME"
  }'
```

---

### 16. 获取类加载器列表
**API**: `classLoaderExplorer.classLoader`

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "classLoaderExplorer.classLoader",
    "target": "YOUR_UNIQUE_NAME",
    "parameters": {
      "page": 1,
      "pageSize": 50
    }
  }'
```

---

## ❌ 不可用的 API

以下 API 虽然在代码中定义，但**无法通过 REST API 调用**：

- `getDetails()` - 无 @ApiMeta 注解
- `getBiggestObjects()` - 无 @ApiMeta 注解
- `getSystemProperties()` - 无 @ApiMeta 注解
- `getEnvVariables()` - 无 @ApiMeta 注解

这些方法可能只能通过 Web UI 或内部调用使用。

---

## Web UI 访问

推荐使用 Web UI 查看完整的分析结果：

```
http://YOUR_HOST:8080/#/heap/YOUR_UNIQUE_NAME
```

Web UI 提供了更友好的可视化界面，可以查看所有分析结果。

---

**更新时间**: 2026-02-03
**测试版本**: Jifa 0.3.0-SNAPSHOT
