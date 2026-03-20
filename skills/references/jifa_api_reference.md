# Jifa API Reference

## Base Configuration

- **Base URL**: `http://21.6.180.85:8080`
- **API Prefix**: All HTTP APIs are prefixed with `/jifa-api`
- **Authentication**: Anonymous access enabled (no login required)

## Core APIs

### 1. Health Check

```
GET /jifa-api/health-check
```

Returns server role and uptime.

### 2. File Management

#### List Files

```
GET /jifa-api/files?type={type}&page={page}&pageSize={pageSize}
```

- `type` (optional): `GC_LOG`, `HEAP_DUMP`, `THREAD_DUMP`, `JFR_FILE`
- `page`: Page number (1-based)
- `pageSize`: Items per page

**Response**: `PageView<FileView>`

```json
{
  "data": [
    {
      "id": 1,
      "uniqueName": "abc123-def456",
      "originalName": "gc.log",
      "type": "GC_LOG",
      "size": 1048576,
      "createdTime": "2024-01-01T00:00:00Z"
    }
  ],
  "page": 1,
  "pageSize": 10,
  "totalSize": 50
}
```

#### Get File Info

```
GET /jifa-api/files/{id-or-unique-name}
```

Returns a single `FileView` object.

#### Upload File (Multipart)

```
POST /jifa-api/files/upload?type={type}
Content-Type: multipart/form-data
```

- `type`: `GC_LOG`, `HEAP_DUMP`, `THREAD_DUMP`, `JFR_FILE`
- `file`: Multipart file

#### Transfer File (OSS/S3/URL/TEXT)

```
POST /jifa-api/files/transfer
Content-Type: application/json
```

**Request Body (FileTransferRequest)**:

```json
{
  "type": "GC_LOG",
  "method": "TEXT",
  "filename": "gc.log",
  "text": "... raw gc log content ..."
}
```

Methods: `OSS`, `S3`, `SCP`, `URL`, `TEXT`

For URL method:
```json
{
  "type": "GC_LOG",
  "method": "URL",
  "url": "http://example.com/gc.log"
}
```

**Response**: File ID for tracking transfer progress.

#### Transfer Progress

```
GET /jifa-api/files/transfer/{transferring-file-id}
```

#### Download File

```
GET /jifa-api/files/{file-id}/download
```

#### Delete File

```
DELETE /jifa-api/files/{file-id}
```

---

## 3. Unified Analysis API

All analysis requests go through a single endpoint:

```
POST /jifa-api/analysis
Content-Type: application/json
X-Enable-SSE: false
```

**Request Body (AnalysisApiRequest)**:

```json
{
  "namespace": "gc-log",
  "api": "metadata",
  "target": "<uniqueName>",
  "parameters": {}
}
```

- `namespace`: `gc-log`, `heap-dump`, `thread-dump`, `jfr-file`
- `api`: Specific API name (see below)
- `target`: File's `uniqueName`
- `parameters`: API-specific parameters (optional)

**SSE Mode**: Set header `X-Enable-SSE: true` to receive SSE events:
- Event `ping`: Heartbeat (every 30s)
- Event `response`: Success response
- Event `error`: Error response

### Common Analysis APIs (All namespaces)

| API | Parameters | Description |
|-----|-----------|-------------|
| `needOptionsForAnalysis` | — | Check if analysis needs user options |
| `analyze` | `options` (Map, optional) | Start analysis |
| `progressOfAnalysis` | — | Get progress: `{state, percent, message}` |
| `release` | — | Release cached analyzer |
| `clean` | — | Clean analyzer cache and error logs |
| `errorLog` | — | Get analysis error log |

**Progress States**: `IN_PROGRESS`, `SUCCESS`, `FAILURE`

---

## 4. GC Log APIs (namespace: `gc-log`)

### metadata

Get GC log metadata.

```json
{
  "namespace": "gc-log",
  "api": "metadata",
  "target": "<uniqueName>"
}
```

**Response (GCLogMetadata)**:

```json
{
  "collector": "G1 GC",
  "logStyle": "unified",
  "startTime": 0.0,
  "endTime": 86400000.0,
  "timestamp": 1704067200000.0,
  "generational": true,
  "pauseless": false,
  "metaspaceCapacityReliable": true,
  "parallelGCThreads": 8,
  "concurrentGCThreads": 2,
  "parentEventTypes": ["Young GC", "Mixed GC", "Full GC"],
  "importantEventTypes": [...],
  "pauseEventTypes": [...],
  "mainPauseEventTypes": [...],
  "allEventTypes": [...],
  "causes": ["G1 Evacuation Pause", "Metadata GC Threshold", ...],
  "analysisConfig": { ... }
}
```

### diagnoseInfo

Get GC diagnostic information — **most important API for root cause analysis**.

```json
{
  "namespace": "gc-log",
  "api": "diagnoseInfo",
  "target": "<uniqueName>",
  "parameters": {
    "config": {
      "timeRange": {"start": 0, "end": 86400000},
      "longPauseThreshold": 400,
      "youngGCFrequentIntervalThreshold": 1000,
      "oldGCFrequentIntervalThreshold": 15000,
      "fullGCFrequentIntervalThreshold": 60000,
      "highOldUsageThreshold": 80,
      "highHeapUsageThreshold": 60,
      "highMetaspaceUsageThreshold": 80,
      "badThroughputThreshold": 90
    }
  }
}
```

**Response (GlobalAbnormalInfo)**:

```json
{
  "mostSeriousProblem": {
    "sites": [{"start": 1000, "end": 2000}],
    "problem": {"name": "longYoungGCPause", "params": {"threshold": 400}},
    "suggestions": [
      {"name": "checkLiveObjects", "params": {}},
      {"name": "enlargeYoungGen", "params": {}}
    ]
  },
  "seriousProblems": {
    "longYoungGCPause": [1000.0, 2000.0, 5000.0],
    "highOldUsed": [3000.0]
  }
}
```

**AbnormalType severity (high to low)**:
- Critical: `outOfMemory`, `allocationStall`
- High: `metaspaceFullGC`, `heapMemoryFullGC`
- Medium: `frequentYoungGC`, `longYoungGCPause`, `systemGC`, `longG1Remark`, `longCMSRemark`
- Low: `badDuration`, `badEventType`, `badCauseFullGC`, `badInterval`, `badPromotion`, `smallYoungGen`, `smallOldGen`, `highHumongousUsed`, `highHeapUsed`, `highOldUsed`, `highMetaspaceUsed`, `badSys`, `badUsr`, `toSpaceExhausted`

### vmOptions

```json
{"namespace": "gc-log", "api": "vmOptions", "target": "<uniqueName>"}
```

### pauseStatistics

```json
{
  "namespace": "gc-log",
  "api": "pauseStatistics",
  "target": "<uniqueName>",
  "parameters": {"range": {"start": 0, "end": 86400000}}
}
```

**Response (PauseStatistics)**:
```json
{
  "throughput": 99.5,
  "pauseAvg": 15.2,
  "pauseMedian": 12.0,
  "pauseP99": 45.0,
  "pauseP999": 120.0,
  "pauseMax": 250.0
}
```

### memoryStatistics

```json
{
  "namespace": "gc-log",
  "api": "memoryStatistics",
  "target": "<uniqueName>",
  "parameters": {"range": {"start": 0, "end": 86400000}}
}
```

**Response (MemoryStatistics)**:
```json
{
  "young": {"capacityAvg": 1073741824, "usedMax": 536870912, "usedAvgAfterFullGC": 0, "usedAvgAfterOldGC": 0},
  "old": {"capacityAvg": 2147483648, "usedMax": 1610612736, "usedAvgAfterFullGC": 536870912, "usedAvgAfterOldGC": 805306368},
  "humongous": {"capacityAvg": 0, "usedMax": 0, "usedAvgAfterFullGC": 0, "usedAvgAfterOldGC": 0},
  "heap": {"capacityAvg": 4294967296, "usedMax": 3221225472, "usedAvgAfterFullGC": 536870912, "usedAvgAfterOldGC": 805306368},
  "metaspace": {"capacityAvg": 134217728, "usedMax": 100663296, "usedAvgAfterFullGC": 0, "usedAvgAfterOldGC": 0}
}
```

### objectStatistics

```json
{
  "namespace": "gc-log",
  "api": "objectStatistics",
  "target": "<uniqueName>",
  "parameters": {"range": {"start": 0, "end": 86400000}}
}
```

**Response (ObjectStatistics)**:
```json
{
  "objectCreationSpeed": 500.0,
  "objectPromotionSpeed": 5.0,
  "objectPromotionAvg": 10485760,
  "objectPromotionMax": 52428800
}
```

### phaseStatistics

```json
{
  "namespace": "gc-log",
  "api": "phaseStatistics",
  "target": "<uniqueName>",
  "parameters": {"range": {"start": 0, "end": 86400000}}
}
```

**Response (PhaseStatistics)**:
```json
{
  "parents": [
    {
      "self": {
        "name": "Young GC",
        "count": 1000,
        "intervalAvg": 5000.0,
        "intervalMin": 1000.0,
        "durationAvg": 15.0,
        "durationMax": 250.0,
        "durationTotal": 15000.0
      },
      "phases": [...],
      "causes": [...]
    }
  ]
}
```

### gcDetails

Get individual GC event details (paginated, with optional filter).

```json
{
  "namespace": "gc-log",
  "api": "gcDetails",
  "target": "<uniqueName>",
  "parameters": {
    "pagingRequest": {"page": 1, "pageSize": 20},
    "filter": {
      "eventType": "Young GC",
      "logTimeLow": 0,
      "logTimeHigh": 86400000,
      "pauseTimeLow": 100
    },
    "config": { ... }
  }
}
```

### pauseDistribution

```json
{
  "namespace": "gc-log",
  "api": "pauseDistribution",
  "target": "<uniqueName>",
  "parameters": {
    "range": {"start": 0, "end": 86400000},
    "partitions": [10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
  }
}
```

### timeGraphData

```json
{
  "namespace": "gc-log",
  "api": "timeGraphData",
  "target": "<uniqueName>",
  "parameters": {
    "dataTypes": ["youngCapacity", "youngUsed", "oldCapacity", "oldUsed"]
  }
}
```

---

## 5. Heap Dump APIs (namespace: `heap-dump`)

### details

```json
{"namespace": "heap-dump", "api": "details", "target": "<uniqueName>"}
```

**Response (Overview.Details)**:
```json
{
  "identifierSize": 8,
  "creationDate": 1704067200000,
  "numberOfObjects": 5000000,
  "numberOfGCRoots": 3000,
  "numberOfClasses": 20000,
  "numberOfClassLoaders": 100,
  "usedHeapSize": 2147483648,
  "jvmOptions": ["-Xmx4g", "-XX:+UseG1GC"]
}
```

### biggestObjects

```json
{"namespace": "heap-dump", "api": "biggestObjects", "target": "<uniqueName>"}
```

**Response**: `List<BigObject>`
```json
[
  {
    "label": "java.util.HashMap @ 0x12345678",
    "objectId": 12345,
    "value": 536870912.0,
    "description": "Retained Size: 512MB (25%)"
  }
]
```

### leak.report

```json
{"namespace": "heap-dump", "api": "leak.report", "target": "<uniqueName>"}
```

**Response (LeakReport)**:
```json
{
  "useful": true,
  "info": "Analysis found potential memory leaks",
  "name": "Leak Suspects Report",
  "slices": [
    {"label": "Suspect 1", "objectId": 123, "value": 40.0, "desc": "40% of heap"}
  ],
  "records": [
    {
      "name": "Problem Suspect 1",
      "desc": "One instance of java.util.HashMap loaded by ...",
      "index": 0,
      "paths": [
        {
          "label": "java.util.HashMap @ 0x1234",
          "shallowSize": 48,
          "retainedSize": 536870912,
          "objectId": 123,
          "objectType": 0,
          "gCRoot": false,
          "children": [...]
        }
      ]
    }
  ]
}
```

### histogram

```json
{
  "namespace": "heap-dump",
  "api": "histogram",
  "target": "<uniqueName>",
  "parameters": {
    "groupBy": "BY_CLASS",
    "sortBy": "retainedSize",
    "ascendingOrder": false,
    "page": 1,
    "pageSize": 50
  }
}
```

### dominatorTree.roots

```json
{
  "namespace": "heap-dump",
  "api": "dominatorTree.roots",
  "target": "<uniqueName>",
  "parameters": {
    "groupBy": "NONE",
    "sortBy": "retainedSize",
    "ascendingOrder": false,
    "page": 1,
    "pageSize": 50
  }
}
```

### threadsSummary / threads

```json
{"namespace": "heap-dump", "api": "threadsSummary", "target": "<uniqueName>"}
```

```json
{
  "namespace": "heap-dump",
  "api": "threads",
  "target": "<uniqueName>",
  "parameters": {
    "sortBy": "retainedSize",
    "ascendingOrder": false,
    "page": 1,
    "pageSize": 20
  }
}
```

### systemProperties

```json
{"namespace": "heap-dump", "api": "systemProperties", "target": "<uniqueName>"}
```

### GCRoots

```json
{"namespace": "heap-dump", "api": "GCRoots", "target": "<uniqueName>"}
```

### duplicatedClasses.classes

```json
{
  "namespace": "heap-dump",
  "api": "duplicatedClasses.classes",
  "target": "<uniqueName>",
  "parameters": {"page": 1, "pageSize": 20}
}
```

### oql / sql

```json
{
  "namespace": "heap-dump",
  "api": "oql",
  "target": "<uniqueName>",
  "parameters": {
    "oql": "SELECT * FROM java.lang.String s WHERE s.value.length > 1000",
    "page": 1,
    "pageSize": 20
  }
}
```

---

## 6. Thread Dump APIs (namespace: `thread-dump`)

### overview

```json
{"namespace": "thread-dump", "api": "overview", "target": "<uniqueName>"}
```

**Response (Overview)**:
```json
{
  "timestamp": 1704067200000,
  "vmInfo": "Java HotSpot(TM) 64-Bit Server VM (25.291-b10 mixed mode)",
  "jniRefs": 100,
  "jniWeakRefs": 50,
  "deadLockCount": 0,
  "errorCount": 0,
  "threadStat": {"counts": [100, 20, 30, 10, 5]},
  "javaThreadStat": {
    "counts": [80, 15, 25, 8, 4],
    "javaCounts": [30, 20, 25, 5],
    "daemonCount": 60
  },
  "jitThreadStat": {"counts": [5, 0, 0, 0, 0]},
  "gcThreadStat": {"counts": [8, 0, 0, 0, 0]},
  "otherThreadStat": {"counts": [7, 5, 5, 2, 1]},
  "threadGroupStat": {
    "main": {"counts": [40, 10, 15, 5, 2]},
    "system": {"counts": [20, 5, 10, 3, 1]}
  },
  "states": ["RUNNABLE", "SLEEPING", "OBJECT_WAIT", "PARKED", "BLOCKED"],
  "javaStates": ["RUNNABLE", "BLOCKED", "WAITING", "TIMED_WAITING"]
}
```

### threads

```json
{
  "namespace": "thread-dump",
  "api": "threads",
  "target": "<uniqueName>",
  "parameters": {
    "paging": {"page": 1, "pageSize": 50}
  }
}
```

Can filter by `name` (String) and `type` (ThreadType: `JAVA`, `JIT`, `GC`, `OTHER`).

### rawContentOfThread

```json
{
  "namespace": "thread-dump",
  "api": "rawContentOfThread",
  "target": "<uniqueName>",
  "parameters": {"id": 5}
}
```

### monitors

```json
{
  "namespace": "thread-dump",
  "api": "monitors",
  "target": "<uniqueName>",
  "parameters": {
    "paging": {"page": 1, "pageSize": 20}
  }
}
```

### callSiteTree

```json
{
  "namespace": "thread-dump",
  "api": "callSiteTree",
  "target": "<uniqueName>",
  "parameters": {
    "parentId": -1,
    "paging": {"page": 1, "pageSize": 20}
  }
}
```

### content

Read raw file content (for direct text inspection).

```json
{
  "namespace": "thread-dump",
  "api": "content",
  "target": "<uniqueName>",
  "parameters": {
    "lineNo": 0,
    "lineLimit": 200
  }
}
```

---

## 7. JFR APIs (namespace: `jfr-file`)

### metadata

```json
{"namespace": "jfr-file", "api": "metadata", "target": "<uniqueName>"}
```

### flameGraph

```json
{
  "namespace": "jfr-file",
  "api": "flameGraph",
  "target": "<uniqueName>",
  "parameters": {
    "dimension": "CPU",
    "include": true,
    "taskSet": []
  }
}
```

---

## Data Structure Reference

### FileType Enum
- `GC_LOG` — GC 日志
- `HEAP_DUMP` — 堆转储
- `THREAD_DUMP` — 线程转储
- `JFR_FILE` — JFR 记录文件

### FileTransferMethod Enum
- `OSS` — 阿里云 OSS
- `S3` — AWS S3
- `SCP` — SCP 传输
- `URL` — HTTP/HTTPS URL
- `TEXT` — 原始文本
- `UPLOAD` — 直接上传

### PagingRequest
```json
{"page": 1, "pageSize": 20}
```
- `page`: 页码，从 1 开始
- `pageSize`: 每页大小

### PageView<T>
```json
{
  "data": [...],
  "page": 1,
  "pageSize": 20,
  "totalSize": 100
}
```

### TimeRange
```json
{"start": 0.0, "end": 86400000.0}
```
- Values in milliseconds

### I18nStringView
```json
{"name": "i18n_key_name", "params": {"key": "value"}}
```
Used in diagnostic messages. The `name` field is the i18n key that describes the problem or suggestion.
