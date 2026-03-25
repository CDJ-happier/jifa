---
name: jifa-analysis
description: This skill provides integration with the Eclipse Jifa Java diagnostic analysis platform. It should be used when users want to analyze Java diagnostic files including GC logs, Heap Dumps, Thread Dumps, and JFR files. The skill fetches analysis results from a self-hosted Jifa service and enables LLM-based root cause analysis. Trigger phrases include "分析GC日志", "分析heap dump", "分析thread dump", "jifa分析", "内存泄漏分析", "GC调优", "线程分析", "JFR分析", or any mention of analyzing Java diagnostic files on the Jifa platform. This skill should also be used when users paste raw GC log content, thread dump text, or provide a URL/filename of a file already on the Jifa platform. It also supports querying ES cluster performance profiling results (firemap, heapdump, jstack, hotthread, task) and analyzing them, as well as converting COS links (cos://...) to downloadable HTTPS URLs. Trigger phrases also include "分析es-xxx的firemap", "分析es-xxx的heapdump", "分析es-xxx的jstack", "查询es-xxx的采集结果", "分析cos://...", or any mention of ES cluster profiling analysis.
---

# Jifa Analysis Skill

## Purpose

Provide deep Java diagnostic analysis by integrating with a self-hosted Eclipse Jifa platform. The skill supports two-level analysis:

1. **Level 1 (Jifa Engine)**: Raw diagnostic files (GC logs, Heap Dumps, Thread Dumps, JFR files) are parsed and analyzed by Jifa's built-in analysis engine.
2. **Level 2 (LLM Analysis)**: Fetch Jifa's structured analysis results via API scripts, then apply LLM reasoning for root cause identification, optimization suggestions, and actionable recommendations.

## Jifa Service Configuration

- **Base URL**: `http://21.6.180.85:8080`
- **API Prefix**: `/jifa-api`
- **Supported File Types**: `GC_LOG`, `HEAP_DUMP`, `THREAD_DUMP`, `JFR_FILE`

## Workflow

### Scenario 1: Analyze an Existing File on Jifa

When the user provides a filename or file ID already present on the Jifa platform:

1. Run `scripts/jifa_client.py list` to find the file and get its `uniqueName`.
2. Determine the file type (GC_LOG, HEAP_DUMP, THREAD_DUMP, JFR_FILE).
3. Run `scripts/jifa_client.py analyze <uniqueName>` to trigger analysis and wait for completion.
4. Run the appropriate data-fetching script based on file type:
   - **GC Log**: `scripts/jifa_client.py gc-report <uniqueName>` — fetches metadata, diagnostics, pause stats, memory stats, object stats, phase stats, VM options.
   - **Heap Dump**: `scripts/jifa_client.py heap-report <uniqueName>` — fetches details, biggest objects, leak report, thread summary.
   - **Thread Dump**: `scripts/jifa_client.py thread-report <uniqueName>` — fetches overview, thread list, monitors, deadlock info.
   - **JFR File**: `scripts/jifa_client.py jfr-report <uniqueName>` — fetches metadata and flame graph data.
5. Analyze the fetched results and provide root cause analysis with actionable recommendations.

### Scenario 2: Analyze Raw Text Content

When the user pastes raw GC log or thread dump content:

1. Run `scripts/jifa_client.py upload-text --type <GC_LOG|THREAD_DUMP> --filename <name> --text "<content>"` to upload the text to Jifa.
2. Wait for analysis to complete.
3. Follow the same data-fetching and analysis steps as Scenario 1.

### Scenario 3: Analyze from URL

When the user provides a URL to a diagnostic file:

1. **Check for existing file**: Extract the filename from the URL, then run `scripts/jifa_client.py search <filename>` to check if a file with the same name already exists on Jifa. If a match is found, skip the upload and go directly to step 4 using the existing file's `uniqueName`.
2. Run `scripts/jifa_client.py upload-url --type <type> --url "<url>"` to transfer the file to Jifa.
3. Poll transfer progress until complete.
4. Follow the same data-fetching and analysis steps as Scenario 1.

## Script Reference

All scripts are in `scripts/` directory. The main entry point is `scripts/jifa_client.py`.

### Usage

```bash
# List all files (optionally filter by type)
python3 scripts/jifa_client.py list [--type GC_LOG|HEAP_DUMP|THREAD_DUMP|JFR_FILE] [--page 1] [--page-size 20]

# Search for a file by name
python3 scripts/jifa_client.py search <filename_keyword>

# Get file info by ID or uniqueName
python3 scripts/jifa_client.py file-info <id_or_unique_name>

# Trigger analysis for a file
python3 scripts/jifa_client.py analyze <uniqueName>

# Get analysis progress
python3 scripts/jifa_client.py progress <uniqueName>

# GC Log full analysis report
python3 scripts/jifa_client.py gc-report <uniqueName>

# GC Log specific APIs
python3 scripts/jifa_client.py gc-metadata <uniqueName>
python3 scripts/jifa_client.py gc-diagnose <uniqueName>
python3 scripts/jifa_client.py gc-pause-stats <uniqueName>
python3 scripts/jifa_client.py gc-memory-stats <uniqueName>
python3 scripts/jifa_client.py gc-object-stats <uniqueName>
python3 scripts/jifa_client.py gc-phase-stats <uniqueName>
python3 scripts/jifa_client.py gc-vm-options <uniqueName>
python3 scripts/jifa_client.py gc-details <uniqueName> [--page 1] [--page-size 20]

# Heap Dump full analysis report
python3 scripts/jifa_client.py heap-report <uniqueName>

# Heap Dump specific APIs
python3 scripts/jifa_client.py heap-details <uniqueName>
python3 scripts/jifa_client.py heap-biggest-objects <uniqueName>
python3 scripts/jifa_client.py heap-leak-report <uniqueName>
python3 scripts/jifa_client.py heap-threads <uniqueName> [--page 1] [--page-size 20]
python3 scripts/jifa_client.py heap-histogram <uniqueName> [--page 1] [--page-size 50]
python3 scripts/jifa_client.py heap-dominator-tree <uniqueName> [--page 1] [--page-size 50]
python3 scripts/jifa_client.py heap-gc-roots <uniqueName>
python3 scripts/jifa_client.py heap-system-properties <uniqueName>
python3 scripts/jifa_client.py heap-duplicated-classes <uniqueName> [--page 1] [--page-size 20]

# Heap Dump interactive deep-dive APIs (drill into objects like the Jifa frontend)
python3 scripts/jifa_client.py heap-outbounds <uniqueName> --object-id <id> [--page 1] [--page-size 25]
python3 scripts/jifa_client.py heap-inbounds <uniqueName> --object-id <id> [--page 1] [--page-size 25]
python3 scripts/jifa_client.py heap-path-to-gc-roots <uniqueName> --object-id <id> [--skip 0] [--count 25]
python3 scripts/jifa_client.py heap-inspector <uniqueName> --object-id <id>
python3 scripts/jifa_client.py heap-dominator-tree-children <uniqueName> --parent-object-id <id> [--page 1] [--page-size 25]
python3 scripts/jifa_client.py heap-merge-path-to-gc-roots <uniqueName> [--class-id <id>] [--page 1] [--page-size 25]
python3 scripts/jifa_client.py heap-class-ref-objects <uniqueName> --class-id <id> [--page 1] [--page-size 25]

# Thread Dump full analysis report
python3 scripts/jifa_client.py thread-report <uniqueName>

# Thread Dump specific APIs
python3 scripts/jifa_client.py thread-overview <uniqueName>
python3 scripts/jifa_client.py thread-list <uniqueName> [--page 1] [--page-size 50]
python3 scripts/jifa_client.py thread-monitors <uniqueName> [--page 1] [--page-size 20]
python3 scripts/jifa_client.py thread-raw-content <uniqueName> --thread-id <id>
python3 scripts/jifa_client.py thread-content <uniqueName> [--line-no 0] [--line-limit 200]

# Thread Dump interactive deep-dive APIs (drill into threads like the Jifa frontend)
python3 scripts/jifa_client.py thread-call-site-tree <uniqueName> [--parent-id 0] [--page 1] [--page-size 25]
python3 scripts/jifa_client.py thread-threads-of-group <uniqueName> --group <group_name> [--page 1] [--page-size 50]
python3 scripts/jifa_client.py thread-counts-by-monitor <uniqueName> --monitor-id <id>
python3 scripts/jifa_client.py thread-by-monitor <uniqueName> --monitor-id <id> --state <PARKING|LOCKED|WAITING_ON|...> [--page 1] [--page-size 50]

# JFR analysis report
python3 scripts/jifa_client.py jfr-report <uniqueName>

# Upload raw text as file
python3 scripts/jifa_client.py upload-text --type <GC_LOG|THREAD_DUMP> --filename <name> --text "<content>"
# Or from a file:
python3 scripts/jifa_client.py upload-text --type <GC_LOG|THREAD_DUMP> --filename <name> --text-file <path>

# Upload from URL
python3 scripts/jifa_client.py upload-url --type <type> --url "<url>"

# Upload local file
python3 scripts/jifa_client.py upload-file --type <type> --file <path>

# Health check
python3 scripts/jifa_client.py health
```

## Analysis Guidelines

### GC Log Analysis Focus Areas

When analyzing GC logs, focus on these key areas and provide findings in order of severity:

1. **Most Serious Problem**: Report `diagnoseInfo.mostSeriousProblem` — the problem description, time ranges, and suggestions.
2. **All Serious Problems**: List all problems in `diagnoseInfo.seriousProblems` with their occurrence time points.
3. **Pause Statistics**: Evaluate throughput, avg/P99/max pause times against thresholds.
4. **Memory Pressure**: Check old generation usage, metaspace usage, heap usage against thresholds.
5. **Object Statistics**: Assess object creation speed, promotion speed, and promotion volume.
6. **GC Collector Assessment**: Based on metadata.collector, evaluate if the GC collector is appropriate.
7. **VM Options Review**: Check for common misconfigurations.

Key abnormal types to watch for (in severity order):
- `outOfMemory`, `allocationStall` — Critical
- `metaspaceFullGC`, `heapMemoryFullGC` — High
- `frequentYoungGC`, `longYoungGCPause`, `systemGC` — Medium
- `longG1Remark`, `longCMSRemark` — Medium
- `highOldUsed`, `highHeapUsed`, `highMetaspaceUsed` — Warning

### Heap Dump Analysis Focus Areas

1. **Leak Report**: `leak.report` — Check if `useful` is true, examine records and shortest paths to GC roots.
2. **Biggest Objects**: Identify dominating objects consuming most heap space.
3. **Overview Details**: Check usedHeapSize, numberOfObjects, numberOfClasses for overall health.
4. **Thread Summary**: Cross-reference thread states with heap usage.
5. **Histogram**: Top memory-consuming classes.
6. **Dominator Tree**: Object ownership hierarchy.

### Thread Dump Analysis Focus Areas

1. **Deadlocks**: Check `overview.deadLockCount` — critical if > 0.
2. **Thread States Distribution**: Analyze the distribution of RUNNABLE, BLOCKED, WAITING, TIMED_WAITING threads.
3. **Lock Contention**: Monitor analysis to find hot locks.
4. **Thread Groups**: Identify overloaded thread pools.
5. **Stack Traces**: Examine blocked and waiting threads for common patterns (database waits, I/O blocks, lock contention).

### JFR Analysis Focus Areas

1. **CPU Flame Graph**: Hot methods, CPU-intensive code paths.
2. **Metadata**: Recording duration, JVM configuration.

## Response Format

Present analysis results in a structured format:

```markdown
## 分析报告：<文件名>

### 概览
- 文件类型：...
- GC 收集器 / JVM 版本：...
- 分析时间范围：...

### 🔴 严重问题
1. **<问题名称>**
   - 描述：...
   - 发生时间：...
   - 建议：...

### 🟡 警告
1. ...

### 📊 关键指标
- 吞吐量：...
- P99 暂停：...
- ...

### 💡 优化建议
1. ...
2. ...

### 📝 详细数据
<可折叠的详细数据>
```

## Scenario 4: Analyze ES Cluster Profiling Results (firemap/heapdump/jstack etc.)

When the user asks to analyze profiling results for an ES cluster (e.g., "帮我分析 es-xxx 集群30分钟前采集的 firemap"):

1. **Extract parameters**: Identify the ES cluster ID (must be `es-xxx` format), profiling type (firemap/heapdump/jstack/hotthread/task), and time range from user's request.
2. **Calculate time**: Convert user's relative time description into absolute `start-time` and `end-time` in `YYYY-MM-DD HH:mm:ss` format. For example, "30分钟前" means `start-time` = now - 30min, `end-time` = now.
3. Run `scripts/es_profiling_client.py query --cluster-id <es-xxx> --item <type> --start-time "<start>" --end-time "<end>"` to query results.
4. Examine the returned results. If any result contains a COS link (URL containing `cos.`):
   - **Extract region**: Parse the COS URL to find the region part from the pattern `.cos.<region>.myqcloud.com` (e.g., `ap-guangzhou`).
   - **Lookup regionId**: Refer to `references/cos_region_mapping.md` to find the corresponding regionId (e.g., `ap-guangzhou` → `1`).
   - Run `scripts/es_profiling_client.py cos-sign --cos-url "<cos_url>" --region-id <regionId>` to convert it to an HTTPS download URL.
5. Based on the profiling type, proceed to analyze:
   - **firemap / jstack / hotthread**: The download URL is typically a flamegraph/thread dump file. Extract the filename from the download URL, run `scripts/jifa_client.py search <filename>` to check if the file already exists on Jifa. If found, use the existing `uniqueName` directly; otherwise, use `scripts/jifa_client.py upload-url --type <JFR_FILE|THREAD_DUMP> --url "<https_url>"` to upload, then analyze using Scenario 1 workflow.
   - **heapdump**: Similarly, search by filename first. If the file exists on Jifa, use it directly; otherwise upload via `scripts/jifa_client.py upload-url --type HEAP_DUMP --url "<https_url>"`. Typically, heapdumps returned by profiling have already been analyzed by Jifa — query results directly using the filename from the profiling response.
   - **task / http**: These are typically structured data results; display and analyze directly from the query response.
6. Provide analysis report following the standard Response Format.

### Profiling Type to Jifa File Type Mapping

| Profiling Item | Jifa File Type | Description                |
| -------------- | -------------- | -------------------------- |
| firemap        | JFR_FILE       | CPU 火焰图采集             |
| jstack         | THREAD_DUMP    | 线程堆栈采集               |
| heapdump       | HEAP_DUMP      | 堆内存快照                 |
| hotthread      | THREAD_DUMP    | 热点线程采集               |
| task           | -              | 任务信息（直接分析文本）   |
| http           | -              | HTTP 请求信息（直接分析 ） |

### Usage

```bash
# 查询 es-xxx 集群指定时间范围的 firemap 采集结果
python3 scripts/es_profiling_client.py query --cluster-id es-xxx --item firemap \
    --start-time "2026-03-25 10:00:00" --end-time "2026-03-25 10:30:00"

# 查询所有采集项
python3 scripts/es_profiling_client.py query --cluster-id es-xxx \
    --start-time "2026-03-25 10:00:00" --end-time "2026-03-25 11:00:00"

# 查询 heapdump
python3 scripts/es_profiling_client.py query --cluster-id es-xxx --item heapdump \
    --start-time "2026-03-25 10:00:00" --end-time "2026-03-25 12:00:00"
```

## Scenario 5: Analyze a COS Link Directly

When the user provides a COS link (e.g., "帮我分析下 cos://bucket.cos.ap-guangzhou.myqcloud.com/path/to/file"):

1. **Extract region from COS URL**: Parse the URL to find the region part from `.cos.<region>.myqcloud.com`.
2. **Lookup regionId**: Refer to `references/cos_region_mapping.md` to find the corresponding regionId.
3. Run `scripts/es_profiling_client.py cos-sign --cos-url "<cos_url>" --region-id <regionId>` to convert COS link to HTTPS download URL.
4. Determine the file type from the filename or user context:
   - `.jfr` or firemap-related → `JFR_FILE`
   - `.hprof` or heapdump-related → `HEAP_DUMP`
   - `.tdump` or jstack/thread-related → `THREAD_DUMP`
   - `.log` with GC content → `GC_LOG`
   - If unclear, ask the user for the file type.
5. **Check for existing file**: Extract the filename from the HTTPS URL, run `scripts/jifa_client.py search <filename>` to check if the file already exists on Jifa. If found, use the existing `uniqueName` directly and skip the upload.
6. Use `scripts/jifa_client.py upload-url --type <type> --url "<https_url>"` to upload to Jifa (only if not found in step 5).
7. Follow Scenario 1 analysis workflow.

### Usage

```bash
# 将 COS 链接转为 HTTPS 下载链接（regionId 由 LLM 查表获得）
python3 scripts/es_profiling_client.py cos-sign --cos-url "cos://bucket.cos.ap-guangzhou.myqcloud.com/path/to/file" --region-id 1

# 北京地域
python3 scripts/es_profiling_client.py cos-sign --cos-url "cos://bucket.cos.ap-beijing.myqcloud.com/file" --region-id 8
```

## ES Profiling Script Reference

The ES profiling client script is at `scripts/es_profiling_client.py`. Environment variable `TCO_ES_MCP_TOKEN` is used for authentication (default provided).

**Important**: 
- `query` 命令的 `--start-time` 和 `--end-time` 为必填参数，LLM 需根据用户描述的相对时间自行计算为绝对时间。
- `cos-sign` 命令的 `--region-id` 为必填参数，LLM 需从 COS URL 中提取地域名后查表 `references/cos_region_mapping.md` 获得对应 regionId。

## API Reference

For detailed API documentation including request/response formats and data structures, refer to `references/jifa_api_reference.md`.
