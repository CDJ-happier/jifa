---
name: jifa-analysis
description: This skill provides integration with the Eclipse Jifa Java diagnostic analysis platform. It should be used when users want to analyze Java diagnostic files including GC logs, Heap Dumps, Thread Dumps, and JFR files. The skill fetches analysis results from a self-hosted Jifa service and enables LLM-based root cause analysis. Trigger phrases include "分析GC日志", "分析heap dump", "分析thread dump", "jifa分析", "内存泄漏分析", "GC调优", "线程分析", "JFR分析", or any mention of analyzing Java diagnostic files on the Jifa platform. This skill should also be used when users paste raw GC log content, thread dump text, or provide a URL/filename of a file already on the Jifa platform.
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

1. Run `scripts/jifa_client.py upload-url --type <type> --url "<url>"` to transfer the file to Jifa.
2. Poll transfer progress until complete.
3. Follow the same data-fetching and analysis steps as Scenario 1.

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
python3 scripts/jifa_client.py thread-call-site-tree <uniqueName> [--parent-id -1] [--page 1] [--page-size 25]
python3 scripts/jifa_client.py thread-threads-of-group <uniqueName> --group <group_name> [--page 1] [--page-size 50]
python3 scripts/jifa_client.py thread-by-monitor <uniqueName> --address <monitor_address> [--page 1] [--page-size 50]

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

## API Reference

For detailed API documentation including request/response formats and data structures, refer to `references/jifa_api_reference.md`.
