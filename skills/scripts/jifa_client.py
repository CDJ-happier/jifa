#!/usr/bin/env python3
"""
Jifa Analysis Platform CLI Client

A command-line client for interacting with the Eclipse Jifa Java diagnostic analysis platform.
Supports file management, analysis triggering, and result retrieval for GC logs, Heap Dumps,
Thread Dumps, and JFR files.

Usage:
    python3 jifa_client.py <command> [options]

Environment Variables:
    JIFA_BASE_URL  - Jifa server URL (default: http://21.6.180.85:8080)
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error


BASE_URL = os.environ.get("JIFA_BASE_URL", "http://21.6.180.85:8080")
API_PREFIX = "/jifa-api"


# ============================================================================
# HTTP Utilities
# ============================================================================

def api_url(path):
    """Build full API URL."""
    return f"{BASE_URL}{API_PREFIX}{path}"


def http_get(path, params=None):
    """Make an HTTP GET request."""
    url = api_url(path)
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        if query:
            url = f"{url}?{query}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data) if data.strip() else None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {e.code} - {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Connection failed - {e.reason}", file=sys.stderr)
        sys.exit(1)


def http_post_json(path, body):
    """Make an HTTP POST request with JSON body."""
    url = api_url(path)
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            resp_data = resp.read().decode("utf-8")
            return json.loads(resp_data) if resp_data.strip() else None
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {e.code} - {body_text}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Connection failed - {e.reason}", file=sys.stderr)
        sys.exit(1)


def http_delete(path):
    """Make an HTTP DELETE request."""
    url = api_url(path)
    req = urllib.request.Request(url, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data) if data.strip() else None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {e.code} - {body}", file=sys.stderr)
        sys.exit(1)


def http_post_multipart(path, file_path, file_type):
    """Make an HTTP POST request with multipart/form-data for file upload."""
    import mimetypes

    boundary = "----JifaClientBoundary" + str(int(time.time()))
    filename = os.path.basename(file_path)
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    with open(file_path, "rb") as f:
        file_data = f.read()

    body_parts = []
    # File field
    body_parts.append(f"--{boundary}".encode())
    body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
    body_parts.append(f"Content-Type: {mime_type}".encode())
    body_parts.append(b"")
    body_parts.append(file_data)
    body_parts.append(f"--{boundary}--".encode())

    body = b"\r\n".join(body_parts)

    url = api_url(f"{path}?type={file_type}")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            resp_data = resp.read().decode("utf-8")
            return json.loads(resp_data) if resp_data.strip() else None
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {e.code} - {body_text}", file=sys.stderr)
        sys.exit(1)


def analysis_request(namespace, api_name, target, parameters=None):
    """Make an analysis API request."""
    body = {
        "namespace": namespace,
        "api": api_name,
        "target": target,
    }
    if parameters:
        body["parameters"] = parameters
    return http_post_json("/analysis", body)


def output_json(data):
    """Pretty print JSON output."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


# ============================================================================
# Namespace Resolution
# ============================================================================

FILE_TYPE_TO_NAMESPACE = {
    "GC_LOG": "gc-log",
    "HEAP_DUMP": "heap-dump",
    "THREAD_DUMP": "thread-dump",
    "JFR_FILE": "jfr-file",
}

NAMESPACE_TO_FILE_TYPE = {v: k for k, v in FILE_TYPE_TO_NAMESPACE.items()}


def resolve_namespace(unique_name):
    """Resolve namespace by fetching file info."""
    info = http_get(f"/files/{unique_name}")
    if info and "type" in info:
        return FILE_TYPE_TO_NAMESPACE.get(info["type"])
    return None


# ============================================================================
# Analysis Helpers
# ============================================================================

def ensure_analyzed(namespace, target):
    """Ensure a file has been analyzed. Trigger analysis if needed and wait for completion."""
    # Check if already analyzed by trying to get progress
    try:
        progress = analysis_request(namespace, "progressOfAnalysis", target)
        if progress and isinstance(progress, dict):
            state = progress.get("state", "")
            if state == "SUCCESS":
                return True
            elif state == "IN_PROGRESS":
                return wait_for_analysis(namespace, target)
            elif state == "FAILURE":
                msg = progress.get("message", "Unknown error")
                print(f"WARNING: Previous analysis failed: {msg}", file=sys.stderr)
                print("Attempting to clean and re-analyze...", file=sys.stderr)
                analysis_request(namespace, "clean", target)
    except Exception:
        pass

    # Trigger analysis
    print("Triggering analysis...", file=sys.stderr)
    try:
        analysis_request(namespace, "analyze", target)
    except Exception as e:
        # May already be analyzed or in progress
        print(f"Note: {e}", file=sys.stderr)

    return wait_for_analysis(namespace, target)


def wait_for_analysis(namespace, target, max_wait=600, interval=3):
    """Wait for analysis to complete."""
    elapsed = 0
    while elapsed < max_wait:
        try:
            progress = analysis_request(namespace, "progressOfAnalysis", target)
            if progress and isinstance(progress, dict):
                state = progress.get("state", "")
                percent = progress.get("percent", 0)
                message = progress.get("message", "")

                if state == "SUCCESS":
                    print("Analysis complete.", file=sys.stderr)
                    return True
                elif state == "FAILURE":
                    print(f"Analysis failed: {message}", file=sys.stderr)
                    return False
                else:
                    print(f"Analyzing... {percent}% - {message}", file=sys.stderr)
        except Exception:
            pass

        time.sleep(interval)
        elapsed += interval

    print(f"Timeout waiting for analysis after {max_wait}s", file=sys.stderr)
    return False


# ============================================================================
# Commands: Health & File Management
# ============================================================================

def cmd_health(args):
    """Check Jifa service health."""
    result = http_get("/health-check")
    output_json(result)


def cmd_list(args):
    """List files on Jifa."""
    params = {
        "page": args.page,
        "pageSize": args.page_size,
    }
    if args.type:
        params["type"] = args.type
    result = http_get("/files", params)
    output_json(result)


def cmd_search(args):
    """Search for a file by keyword in all pages."""
    keyword = args.keyword.lower()
    page = 1
    page_size = 50
    found = []

    while True:
        params = {"page": page, "pageSize": page_size}
        result = http_get("/files", params)
        if not result or "data" not in result:
            break

        for f in result["data"]:
            name = (f.get("originalName") or "").lower()
            unique = (f.get("uniqueName") or "").lower()
            if keyword in name or keyword in unique:
                found.append(f)

        if page * page_size >= result.get("totalSize", 0):
            break
        page += 1

    output_json({"found": len(found), "files": found})


def cmd_file_info(args):
    """Get file info by ID or uniqueName."""
    result = http_get(f"/files/{args.id_or_name}")
    output_json(result)


def cmd_delete_file(args):
    """Delete a file."""
    result = http_delete(f"/files/{args.file_id}")
    print(f"Deleted file {args.file_id}", file=sys.stderr)
    if result:
        output_json(result)


# ============================================================================
# Commands: Upload
# ============================================================================

def cmd_upload_text(args):
    """Upload raw text content as a file."""
    text_content = args.text
    if args.text_file:
        with open(args.text_file, "r") as f:
            text_content = f.read()

    if not text_content:
        print("ERROR: No text content provided. Use --text or --text-file.", file=sys.stderr)
        sys.exit(1)

    body = {
        "type": args.type,
        "method": "TEXT",
        "filename": args.filename,
        "text": text_content,
    }
    result = http_post_json("/files/transfer", body)
    output_json(result)

    # If result contains an ID, wait for transfer to complete
    if result and isinstance(result, (int, float)):
        wait_for_transfer(int(result))


def cmd_upload_url(args):
    """Upload file from URL."""
    body = {
        "type": args.type,
        "method": "URL",
        "url": args.url,
    }
    result = http_post_json("/files/transfer", body)
    output_json(result)

    if result and isinstance(result, (int, float)):
        wait_for_transfer(int(result))


def cmd_upload_file(args):
    """Upload a local file."""
    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    result = http_post_multipart("/files/upload", args.file, args.type)
    output_json(result)


def wait_for_transfer(transfer_id, max_wait=600, interval=3):
    """Wait for file transfer to complete."""
    elapsed = 0
    while elapsed < max_wait:
        try:
            progress = http_get(f"/files/transfer/{transfer_id}")
            if progress:
                output_json(progress)
                state = progress.get("state", "")
                if state in ("SUCCESS", "COMPLETE"):
                    return True
                elif state in ("FAILURE", "ERROR"):
                    return False
        except Exception:
            pass
        time.sleep(interval)
        elapsed += interval
    print(f"Timeout waiting for transfer after {max_wait}s", file=sys.stderr)
    return False


# ============================================================================
# Commands: Analysis Trigger
# ============================================================================

def cmd_analyze(args):
    """Trigger analysis for a file."""
    namespace = args.namespace
    if not namespace:
        namespace = resolve_namespace(args.target)
    if not namespace:
        print("ERROR: Could not determine file type. Use --namespace to specify.", file=sys.stderr)
        sys.exit(1)

    success = ensure_analyzed(namespace, args.target)
    if success:
        print(json.dumps({"status": "SUCCESS", "target": args.target, "namespace": namespace}))
    else:
        print(json.dumps({"status": "FAILURE", "target": args.target, "namespace": namespace}))
        sys.exit(1)


def cmd_progress(args):
    """Get analysis progress."""
    namespace = args.namespace
    if not namespace:
        namespace = resolve_namespace(args.target)
    if not namespace:
        print("ERROR: Could not determine file type.", file=sys.stderr)
        sys.exit(1)
    result = analysis_request(namespace, "progressOfAnalysis", args.target)
    output_json(result)


# ============================================================================
# Commands: GC Log Analysis
# ============================================================================

def cmd_gc_report(args):
    """Get comprehensive GC log analysis report."""
    target = args.target
    ns = "gc-log"

    ensure_analyzed(ns, target)

    report = {}

    # Metadata
    print("Fetching metadata...", file=sys.stderr)
    report["metadata"] = analysis_request(ns, "metadata", target)

    # Diagnose info
    print("Fetching diagnosis...", file=sys.stderr)
    config = {}
    if report["metadata"] and "analysisConfig" in report["metadata"]:
        config = report["metadata"]["analysisConfig"]
    report["diagnoseInfo"] = analysis_request(ns, "diagnoseInfo", target, {"config": config})

    # Pause statistics
    print("Fetching pause statistics...", file=sys.stderr)
    report["pauseStatistics"] = analysis_request(ns, "pauseStatistics", target)

    # Memory statistics
    print("Fetching memory statistics...", file=sys.stderr)
    report["memoryStatistics"] = analysis_request(ns, "memoryStatistics", target)

    # Object statistics
    print("Fetching object statistics...", file=sys.stderr)
    report["objectStatistics"] = analysis_request(ns, "objectStatistics", target)

    # Phase statistics
    print("Fetching phase statistics...", file=sys.stderr)
    report["phaseStatistics"] = analysis_request(ns, "phaseStatistics", target)

    # VM options
    print("Fetching VM options...", file=sys.stderr)
    report["vmOptions"] = analysis_request(ns, "vmOptions", target)

    output_json(report)


def cmd_gc_metadata(args):
    """Get GC log metadata."""
    ensure_analyzed("gc-log", args.target)
    result = analysis_request("gc-log", "metadata", args.target)
    output_json(result)


def cmd_gc_diagnose(args):
    """Get GC diagnostic information."""
    ensure_analyzed("gc-log", args.target)

    config = {}
    if args.config:
        config = json.loads(args.config)
    else:
        # Get default config from metadata
        meta = analysis_request("gc-log", "metadata", args.target)
        if meta and "analysisConfig" in meta:
            config = meta["analysisConfig"]

    result = analysis_request("gc-log", "diagnoseInfo", args.target, {"config": config})
    output_json(result)


def cmd_gc_pause_stats(args):
    """Get GC pause statistics."""
    ensure_analyzed("gc-log", args.target)
    params = {}
    if args.start is not None and args.end is not None:
        params["range"] = {"start": args.start, "end": args.end}
    result = analysis_request("gc-log", "pauseStatistics", args.target, params if params else None)
    output_json(result)


def cmd_gc_memory_stats(args):
    """Get GC memory statistics."""
    ensure_analyzed("gc-log", args.target)
    params = {}
    if args.start is not None and args.end is not None:
        params["range"] = {"start": args.start, "end": args.end}
    result = analysis_request("gc-log", "memoryStatistics", args.target, params if params else None)
    output_json(result)


def cmd_gc_object_stats(args):
    """Get GC object statistics."""
    ensure_analyzed("gc-log", args.target)
    params = {}
    if args.start is not None and args.end is not None:
        params["range"] = {"start": args.start, "end": args.end}
    result = analysis_request("gc-log", "objectStatistics", args.target, params if params else None)
    output_json(result)


def cmd_gc_phase_stats(args):
    """Get GC phase statistics."""
    ensure_analyzed("gc-log", args.target)
    params = {}
    if args.start is not None and args.end is not None:
        params["range"] = {"start": args.start, "end": args.end}
    result = analysis_request("gc-log", "phaseStatistics", args.target, params if params else None)
    output_json(result)


def cmd_gc_vm_options(args):
    """Get VM options from GC log."""
    ensure_analyzed("gc-log", args.target)
    result = analysis_request("gc-log", "vmOptions", args.target)
    output_json(result)


def cmd_gc_details(args):
    """Get GC event details (paginated)."""
    ensure_analyzed("gc-log", args.target)
    params = {
        "pagingRequest": {"page": args.page, "pageSize": args.page_size},
    }
    if args.event_type or args.pause_time_low:
        filter_params = {}
        if args.event_type:
            filter_params["eventType"] = args.event_type
        if args.pause_time_low:
            filter_params["pauseTimeLow"] = args.pause_time_low
        params["filter"] = filter_params

    # Get config
    meta = analysis_request("gc-log", "metadata", args.target)
    if meta and "analysisConfig" in meta:
        params["config"] = meta["analysisConfig"]

    result = analysis_request("gc-log", "gcDetails", args.target, params)
    output_json(result)


# ============================================================================
# Commands: Heap Dump Analysis
# ============================================================================

def cmd_heap_report(args):
    """Get comprehensive Heap Dump analysis report."""
    target = args.target
    ns = "heap-dump"

    ensure_analyzed(ns, target)

    report = {}

    print("Fetching details...", file=sys.stderr)
    report["details"] = analysis_request(ns, "details", target)

    print("Fetching biggest objects...", file=sys.stderr)
    report["biggestObjects"] = analysis_request(ns, "biggestObjects", target)

    print("Fetching leak report...", file=sys.stderr)
    report["leakReport"] = analysis_request(ns, "leak.report", target)

    print("Fetching thread summary...", file=sys.stderr)
    try:
        report["threadsSummary"] = analysis_request(ns, "threadsSummary", target)
    except Exception:
        report["threadsSummary"] = None

    print("Fetching system properties...", file=sys.stderr)
    try:
        report["systemProperties"] = analysis_request(ns, "systemProperties", target)
    except Exception:
        report["systemProperties"] = None

    print("Fetching GC roots...", file=sys.stderr)
    try:
        report["gcRoots"] = analysis_request(ns, "GCRoots", target)
    except Exception:
        report["gcRoots"] = None

    output_json(report)


def cmd_heap_details(args):
    """Get heap dump overview details."""
    ensure_analyzed("heap-dump", args.target)
    result = analysis_request("heap-dump", "details", args.target)
    output_json(result)


def cmd_heap_biggest_objects(args):
    """Get biggest objects in heap dump."""
    ensure_analyzed("heap-dump", args.target)
    result = analysis_request("heap-dump", "biggestObjects", args.target)
    output_json(result)


def cmd_heap_leak_report(args):
    """Get heap dump leak report."""
    ensure_analyzed("heap-dump", args.target)
    result = analysis_request("heap-dump", "leak.report", args.target)
    output_json(result)


def cmd_heap_threads(args):
    """Get threads from heap dump."""
    ensure_analyzed("heap-dump", args.target)
    params = {
        "sortBy": "retainedSize",
        "ascendingOrder": False,
        "page": args.page,
        "pageSize": args.page_size,
    }
    result = analysis_request("heap-dump", "threads", args.target, params)
    output_json(result)


def cmd_heap_histogram(args):
    """Get heap dump histogram."""
    ensure_analyzed("heap-dump", args.target)
    params = {
        "groupBy": "BY_CLASS",
        "sortBy": "retainedSize",
        "ascendingOrder": False,
        "page": args.page,
        "pageSize": args.page_size,
    }
    result = analysis_request("heap-dump", "histogram", args.target, params)
    output_json(result)


def cmd_heap_dominator_tree(args):
    """Get heap dump dominator tree roots."""
    ensure_analyzed("heap-dump", args.target)
    params = {
        "groupBy": "NONE",
        "sortBy": "retainedSize",
        "ascendingOrder": False,
        "page": args.page,
        "pageSize": args.page_size,
    }
    result = analysis_request("heap-dump", "dominatorTree.roots", args.target, params)
    output_json(result)


def cmd_heap_gc_roots(args):
    """Get GC roots from heap dump."""
    ensure_analyzed("heap-dump", args.target)
    result = analysis_request("heap-dump", "GCRoots", args.target)
    output_json(result)


def cmd_heap_system_properties(args):
    """Get system properties from heap dump."""
    ensure_analyzed("heap-dump", args.target)
    result = analysis_request("heap-dump", "systemProperties", args.target)
    output_json(result)


def cmd_heap_duplicated_classes(args):
    """Get duplicated classes from heap dump."""
    ensure_analyzed("heap-dump", args.target)
    params = {
        "page": args.page,
        "pageSize": args.page_size,
    }
    result = analysis_request("heap-dump", "duplicatedClasses.classes", args.target, params)
    output_json(result)


# ============================================================================
# Commands: Heap Dump Interactive / Deep-dive APIs
# ============================================================================

def cmd_heap_outbounds(args):
    """Get outbound references of an object in heap dump."""
    ensure_analyzed("heap-dump", args.target)
    params = {
        "objectId": args.object_id,
        "page": args.page,
        "pageSize": args.page_size,
    }
    result = analysis_request("heap-dump", "outbounds", args.target, params)
    output_json(result)


def cmd_heap_inbounds(args):
    """Get inbound references (referrers) of an object in heap dump."""
    ensure_analyzed("heap-dump", args.target)
    params = {
        "objectId": args.object_id,
        "page": args.page,
        "pageSize": args.page_size,
    }
    result = analysis_request("heap-dump", "inbounds", args.target, params)
    output_json(result)


def cmd_heap_path_to_gc_roots(args):
    """Get path from an object to GC roots in heap dump."""
    ensure_analyzed("heap-dump", args.target)
    params = {
        "objectId": args.object_id,
        "skip": args.skip,
        "count": args.count,
    }
    result = analysis_request("heap-dump", "pathToGCRoots", args.target, params)
    output_json(result)


def cmd_heap_inspector(args):
    """Get inspector object view and value for a specific object in heap dump."""
    ensure_analyzed("heap-dump", args.target)
    report = {}
    params = {"objectId": args.object_id}

    print("Fetching object view...", file=sys.stderr)
    report["objectView"] = analysis_request("heap-dump", "inspector.objectView", args.target, params)

    print("Fetching object value...", file=sys.stderr)
    try:
        report["value"] = analysis_request("heap-dump", "inspector.value", args.target, params)
    except Exception:
        report["value"] = None

    output_json(report)


def cmd_heap_dominator_tree_children(args):
    """Get children of a dominator tree node in heap dump."""
    ensure_analyzed("heap-dump", args.target)
    params = {
        "parentObjectId": args.parent_object_id,
        "sortBy": "retainedSize",
        "ascendingOrder": False,
        "idPathInResultTree": [],
        "page": args.page,
        "pageSize": args.page_size,
    }
    result = analysis_request("heap-dump", "dominatorTree.children", args.target, params)
    output_json(result)


def cmd_heap_merge_path_to_gc_roots(args):
    """Get merged paths to GC roots for class-level analysis."""
    ensure_analyzed("heap-dump", args.target)
    params = {
        "groupBy": "FROM_GC_ROOTS",
        "page": args.page,
        "pageSize": args.page_size,
    }
    if args.class_id is not None:
        params["classId"] = args.class_id
    result = analysis_request("heap-dump", "mergePathToGCRoots.roots.byClass", args.target, params)
    output_json(result)


def cmd_heap_class_ref_objects(args):
    """Get objects of a specific class from histogram (for deeper inspection)."""
    ensure_analyzed("heap-dump", args.target)
    params = {
        "classId": args.class_id,
        "page": args.page,
        "pageSize": args.page_size,
    }
    result = analysis_request("heap-dump", "histogram.objects", args.target, params)
    output_json(result)


# ============================================================================
# Commands: Thread Dump Analysis
# ============================================================================

def cmd_thread_report(args):
    """Get comprehensive Thread Dump analysis report."""
    target = args.target
    ns = "thread-dump"

    ensure_analyzed(ns, target)

    report = {}

    print("Fetching overview...", file=sys.stderr)
    report["overview"] = analysis_request(ns, "overview", target)

    print("Fetching thread list...", file=sys.stderr)
    report["threads"] = analysis_request(ns, "threads", target, {
        "paging": {"page": 1, "pageSize": 200}
    })

    print("Fetching monitors...", file=sys.stderr)
    try:
        report["monitors"] = analysis_request(ns, "monitors", target, {
            "paging": {"page": 1, "pageSize": 50}
        })
    except Exception:
        report["monitors"] = None

    output_json(report)


def cmd_thread_overview(args):
    """Get thread dump overview."""
    ensure_analyzed("thread-dump", args.target)
    result = analysis_request("thread-dump", "overview", args.target)
    output_json(result)


def cmd_thread_list(args):
    """Get thread list from thread dump."""
    ensure_analyzed("thread-dump", args.target)
    params = {
        "paging": {"page": args.page, "pageSize": args.page_size}
    }
    if args.name:
        params["name"] = args.name
    if args.thread_type:
        params["type"] = args.thread_type
    result = analysis_request("thread-dump", "threads", args.target, params)
    output_json(result)


def cmd_thread_monitors(args):
    """Get monitors from thread dump."""
    ensure_analyzed("thread-dump", args.target)
    params = {"paging": {"page": args.page, "pageSize": args.page_size}}
    result = analysis_request("thread-dump", "monitors", args.target, params)
    output_json(result)


def cmd_thread_raw_content(args):
    """Get raw content of a specific thread."""
    ensure_analyzed("thread-dump", args.target)
    result = analysis_request("thread-dump", "rawContentOfThread", args.target, {"id": args.thread_id})
    output_json(result)


def cmd_thread_call_site_tree(args):
    """Get call site tree (aggregated stack traces) from thread dump."""
    ensure_analyzed("thread-dump", args.target)
    params = {
        "parentId": args.parent_id,
        "page": args.page,
        "pageSize": args.page_size,
    }
    result = analysis_request("thread-dump", "callSiteTree", args.target, params)
    output_json(result)


def cmd_thread_threads_of_group(args):
    """Get threads belonging to a specific thread group."""
    ensure_analyzed("thread-dump", args.target)
    params = {
        "group": args.group,
        "paging": {"page": args.page, "pageSize": args.page_size},
    }
    result = analysis_request("thread-dump", "threadsOfGroup", args.target, params)
    output_json(result)


def cmd_thread_by_monitor(args):
    """Get threads associated with a specific monitor."""
    ensure_analyzed("thread-dump", args.target)
    params = {
        "address": args.address,
        "paging": {"page": args.page, "pageSize": args.page_size},
    }
    result = analysis_request("thread-dump", "threadsByMonitor", args.target, params)
    output_json(result)


def cmd_thread_content(args):
    """Get raw file content from thread dump."""
    ensure_analyzed("thread-dump", args.target)
    result = analysis_request("thread-dump", "content", args.target, {
        "lineNo": args.line_no,
        "lineLimit": args.line_limit,
    })
    output_json(result)


# ============================================================================
# Commands: JFR Analysis
# ============================================================================

def cmd_jfr_report(args):
    """Get JFR analysis report."""
    target = args.target
    ns = "jfr-file"

    ensure_analyzed(ns, target)

    report = {}

    print("Fetching metadata...", file=sys.stderr)
    report["metadata"] = analysis_request(ns, "metadata", target)

    print("Fetching CPU flame graph...", file=sys.stderr)
    try:
        report["cpuFlameGraph"] = analysis_request(ns, "flameGraph", target, {
            "dimension": "CPU",
            "include": True,
            "taskSet": [],
        })
    except Exception:
        report["cpuFlameGraph"] = None

    output_json(report)


def cmd_jfr_metadata(args):
    """Get JFR metadata."""
    ensure_analyzed("jfr-file", args.target)
    result = analysis_request("jfr-file", "metadata", args.target)
    output_json(result)


# ============================================================================
# Argument Parser
# ============================================================================

def build_parser():
    parser = argparse.ArgumentParser(
        description="Jifa Analysis Platform CLI Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Health
    subparsers.add_parser("health", help="Check Jifa service health")

    # List files
    p_list = subparsers.add_parser("list", help="List files on Jifa")
    p_list.add_argument("--type", choices=["GC_LOG", "HEAP_DUMP", "THREAD_DUMP", "JFR_FILE"],
                        help="Filter by file type")
    p_list.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    p_list.add_argument("--page-size", type=int, default=20, help="Page size (default: 20)")

    # Search
    p_search = subparsers.add_parser("search", help="Search for a file by name keyword")
    p_search.add_argument("keyword", help="Filename keyword to search for")

    # File info
    p_info = subparsers.add_parser("file-info", help="Get file info by ID or uniqueName")
    p_info.add_argument("id_or_name", help="File ID or uniqueName")

    # Delete file
    p_delete = subparsers.add_parser("delete-file", help="Delete a file")
    p_delete.add_argument("file_id", help="File ID to delete")

    # Upload text
    p_ut = subparsers.add_parser("upload-text", help="Upload raw text as a file")
    p_ut.add_argument("--type", required=True, choices=["GC_LOG", "THREAD_DUMP"],
                      help="File type")
    p_ut.add_argument("--filename", required=True, help="Filename for the uploaded text")
    p_ut.add_argument("--text", help="Raw text content")
    p_ut.add_argument("--text-file", help="Path to text file to upload")

    # Upload URL
    p_uu = subparsers.add_parser("upload-url", help="Upload file from URL")
    p_uu.add_argument("--type", required=True,
                      choices=["GC_LOG", "HEAP_DUMP", "THREAD_DUMP", "JFR_FILE"],
                      help="File type")
    p_uu.add_argument("--url", required=True, help="URL to download file from")

    # Upload file
    p_uf = subparsers.add_parser("upload-file", help="Upload a local file")
    p_uf.add_argument("--type", required=True,
                      choices=["GC_LOG", "HEAP_DUMP", "THREAD_DUMP", "JFR_FILE"],
                      help="File type")
    p_uf.add_argument("--file", required=True, help="Local file path")

    # Analyze
    p_analyze = subparsers.add_parser("analyze", help="Trigger analysis for a file")
    p_analyze.add_argument("target", help="File uniqueName")
    p_analyze.add_argument("--namespace", help="Override namespace (gc-log, heap-dump, thread-dump, jfr-file)")

    # Progress
    p_progress = subparsers.add_parser("progress", help="Get analysis progress")
    p_progress.add_argument("target", help="File uniqueName")
    p_progress.add_argument("--namespace", help="Override namespace")

    # ---- GC Log Commands ----
    p_gc_report = subparsers.add_parser("gc-report", help="Get full GC log analysis report")
    p_gc_report.add_argument("target", help="File uniqueName")

    p_gc_meta = subparsers.add_parser("gc-metadata", help="Get GC log metadata")
    p_gc_meta.add_argument("target", help="File uniqueName")

    p_gc_diag = subparsers.add_parser("gc-diagnose", help="Get GC diagnostic information")
    p_gc_diag.add_argument("target", help="File uniqueName")
    p_gc_diag.add_argument("--config", help="Analysis config as JSON string")

    p_gc_pause = subparsers.add_parser("gc-pause-stats", help="Get GC pause statistics")
    p_gc_pause.add_argument("target", help="File uniqueName")
    p_gc_pause.add_argument("--start", type=float, help="Time range start (ms)")
    p_gc_pause.add_argument("--end", type=float, help="Time range end (ms)")

    p_gc_mem = subparsers.add_parser("gc-memory-stats", help="Get GC memory statistics")
    p_gc_mem.add_argument("target", help="File uniqueName")
    p_gc_mem.add_argument("--start", type=float, help="Time range start (ms)")
    p_gc_mem.add_argument("--end", type=float, help="Time range end (ms)")

    p_gc_obj = subparsers.add_parser("gc-object-stats", help="Get GC object statistics")
    p_gc_obj.add_argument("target", help="File uniqueName")
    p_gc_obj.add_argument("--start", type=float, help="Time range start (ms)")
    p_gc_obj.add_argument("--end", type=float, help="Time range end (ms)")

    p_gc_phase = subparsers.add_parser("gc-phase-stats", help="Get GC phase statistics")
    p_gc_phase.add_argument("target", help="File uniqueName")
    p_gc_phase.add_argument("--start", type=float, help="Time range start (ms)")
    p_gc_phase.add_argument("--end", type=float, help="Time range end (ms)")

    p_gc_vm = subparsers.add_parser("gc-vm-options", help="Get VM options from GC log")
    p_gc_vm.add_argument("target", help="File uniqueName")

    p_gc_details = subparsers.add_parser("gc-details", help="Get GC event details")
    p_gc_details.add_argument("target", help="File uniqueName")
    p_gc_details.add_argument("--page", type=int, default=1, help="Page number")
    p_gc_details.add_argument("--page-size", type=int, default=20, help="Page size")
    p_gc_details.add_argument("--event-type", help="Filter by event type")
    p_gc_details.add_argument("--pause-time-low", type=float, help="Min pause time (ms)")

    # ---- Heap Dump Commands ----
    p_heap_report = subparsers.add_parser("heap-report", help="Get full Heap Dump analysis report")
    p_heap_report.add_argument("target", help="File uniqueName")

    p_heap_details = subparsers.add_parser("heap-details", help="Get heap dump overview details")
    p_heap_details.add_argument("target", help="File uniqueName")

    p_heap_big = subparsers.add_parser("heap-biggest-objects", help="Get biggest objects")
    p_heap_big.add_argument("target", help="File uniqueName")

    p_heap_leak = subparsers.add_parser("heap-leak-report", help="Get leak report")
    p_heap_leak.add_argument("target", help="File uniqueName")

    p_heap_threads = subparsers.add_parser("heap-threads", help="Get threads from heap dump")
    p_heap_threads.add_argument("target", help="File uniqueName")
    p_heap_threads.add_argument("--page", type=int, default=1)
    p_heap_threads.add_argument("--page-size", type=int, default=20)

    p_heap_hist = subparsers.add_parser("heap-histogram", help="Get heap histogram")
    p_heap_hist.add_argument("target", help="File uniqueName")
    p_heap_hist.add_argument("--page", type=int, default=1)
    p_heap_hist.add_argument("--page-size", type=int, default=50)

    p_heap_dom = subparsers.add_parser("heap-dominator-tree", help="Get dominator tree roots")
    p_heap_dom.add_argument("target", help="File uniqueName")
    p_heap_dom.add_argument("--page", type=int, default=1)
    p_heap_dom.add_argument("--page-size", type=int, default=50)

    p_heap_gc = subparsers.add_parser("heap-gc-roots", help="Get GC roots")
    p_heap_gc.add_argument("target", help="File uniqueName")

    p_heap_sp = subparsers.add_parser("heap-system-properties", help="Get system properties")
    p_heap_sp.add_argument("target", help="File uniqueName")

    p_heap_dup = subparsers.add_parser("heap-duplicated-classes", help="Get duplicated classes")
    p_heap_dup.add_argument("target", help="File uniqueName")
    p_heap_dup.add_argument("--page", type=int, default=1)
    p_heap_dup.add_argument("--page-size", type=int, default=20)

    # ---- Heap Dump Interactive/Deep-dive Commands ----
    p_heap_out = subparsers.add_parser("heap-outbounds", help="Get outbound references of an object")
    p_heap_out.add_argument("target", help="File uniqueName")
    p_heap_out.add_argument("--object-id", type=int, required=True, help="Object ID")
    p_heap_out.add_argument("--page", type=int, default=1)
    p_heap_out.add_argument("--page-size", type=int, default=25)

    p_heap_in = subparsers.add_parser("heap-inbounds", help="Get inbound references (referrers) of an object")
    p_heap_in.add_argument("target", help="File uniqueName")
    p_heap_in.add_argument("--object-id", type=int, required=True, help="Object ID")
    p_heap_in.add_argument("--page", type=int, default=1)
    p_heap_in.add_argument("--page-size", type=int, default=25)

    p_heap_path = subparsers.add_parser("heap-path-to-gc-roots", help="Get path from object to GC roots")
    p_heap_path.add_argument("target", help="File uniqueName")
    p_heap_path.add_argument("--object-id", type=int, required=True, help="Object ID")
    p_heap_path.add_argument("--skip", type=int, default=0, help="Number of paths to skip")
    p_heap_path.add_argument("--count", type=int, default=25, help="Number of paths to return")

    p_heap_insp = subparsers.add_parser("heap-inspector", help="Get inspector view and value for an object")
    p_heap_insp.add_argument("target", help="File uniqueName")
    p_heap_insp.add_argument("--object-id", type=int, required=True, help="Object ID")

    p_heap_dom_ch = subparsers.add_parser("heap-dominator-tree-children", help="Get children of a dominator tree node")
    p_heap_dom_ch.add_argument("target", help="File uniqueName")
    p_heap_dom_ch.add_argument("--parent-object-id", type=int, required=True, help="Parent object ID")
    p_heap_dom_ch.add_argument("--page", type=int, default=1)
    p_heap_dom_ch.add_argument("--page-size", type=int, default=25)

    p_heap_merge = subparsers.add_parser("heap-merge-path-to-gc-roots", help="Get merged paths to GC roots by class")
    p_heap_merge.add_argument("target", help="File uniqueName")
    p_heap_merge.add_argument("--class-id", type=int, help="Class object ID (optional)")
    p_heap_merge.add_argument("--page", type=int, default=1)
    p_heap_merge.add_argument("--page-size", type=int, default=25)

    p_heap_cref = subparsers.add_parser("heap-class-ref-objects", help="Get objects of a specific class from histogram")
    p_heap_cref.add_argument("target", help="File uniqueName")
    p_heap_cref.add_argument("--class-id", type=int, required=True, help="Class object ID")
    p_heap_cref.add_argument("--page", type=int, default=1)
    p_heap_cref.add_argument("--page-size", type=int, default=25)

    # ---- Thread Dump Commands ----
    p_td_report = subparsers.add_parser("thread-report", help="Get full Thread Dump analysis report")
    p_td_report.add_argument("target", help="File uniqueName")

    p_td_overview = subparsers.add_parser("thread-overview", help="Get thread dump overview")
    p_td_overview.add_argument("target", help="File uniqueName")

    p_td_list = subparsers.add_parser("thread-list", help="Get thread list")
    p_td_list.add_argument("target", help="File uniqueName")
    p_td_list.add_argument("--page", type=int, default=1)
    p_td_list.add_argument("--page-size", type=int, default=50)
    p_td_list.add_argument("--name", help="Filter by thread name")
    p_td_list.add_argument("--thread-type", choices=["JAVA", "JIT", "GC", "OTHER"],
                           help="Filter by thread type")

    p_td_monitors = subparsers.add_parser("thread-monitors", help="Get monitors")
    p_td_monitors.add_argument("target", help="File uniqueName")
    p_td_monitors.add_argument("--page", type=int, default=1)
    p_td_monitors.add_argument("--page-size", type=int, default=20)

    p_td_raw = subparsers.add_parser("thread-raw-content", help="Get raw content of a thread")
    p_td_raw.add_argument("target", help="File uniqueName")
    p_td_raw.add_argument("--thread-id", type=int, required=True, help="Thread ID")

    p_td_cst = subparsers.add_parser("thread-call-site-tree", help="Get call site tree (aggregated stack traces)")
    p_td_cst.add_argument("target", help="File uniqueName")
    p_td_cst.add_argument("--parent-id", type=int, default=0, help="Parent node ID (0 for root)")
    p_td_cst.add_argument("--page", type=int, default=1)
    p_td_cst.add_argument("--page-size", type=int, default=25)

    p_td_grp = subparsers.add_parser("thread-threads-of-group", help="Get threads of a specific group")
    p_td_grp.add_argument("target", help="File uniqueName")
    p_td_grp.add_argument("--group", required=True, help="Thread group name")
    p_td_grp.add_argument("--page", type=int, default=1)
    p_td_grp.add_argument("--page-size", type=int, default=50)

    p_td_bm = subparsers.add_parser("thread-by-monitor", help="Get threads associated with a monitor")
    p_td_bm.add_argument("target", help="File uniqueName")
    p_td_bm.add_argument("--address", required=True, help="Monitor address")
    p_td_bm.add_argument("--page", type=int, default=1)
    p_td_bm.add_argument("--page-size", type=int, default=50)

    p_td_content = subparsers.add_parser("thread-content", help="Get raw file content")
    p_td_content.add_argument("target", help="File uniqueName")
    p_td_content.add_argument("--line-no", type=int, default=0, help="Start line number")
    p_td_content.add_argument("--line-limit", type=int, default=200, help="Number of lines to read")

    # ---- JFR Commands ----
    p_jfr_report = subparsers.add_parser("jfr-report", help="Get JFR analysis report")
    p_jfr_report.add_argument("target", help="File uniqueName")

    p_jfr_meta = subparsers.add_parser("jfr-metadata", help="Get JFR metadata")
    p_jfr_meta.add_argument("target", help="File uniqueName")

    return parser


# ============================================================================
# Main
# ============================================================================

COMMAND_MAP = {
    "health": cmd_health,
    "list": cmd_list,
    "search": cmd_search,
    "file-info": cmd_file_info,
    "delete-file": cmd_delete_file,
    "upload-text": cmd_upload_text,
    "upload-url": cmd_upload_url,
    "upload-file": cmd_upload_file,
    "analyze": cmd_analyze,
    "progress": cmd_progress,
    # GC Log
    "gc-report": cmd_gc_report,
    "gc-metadata": cmd_gc_metadata,
    "gc-diagnose": cmd_gc_diagnose,
    "gc-pause-stats": cmd_gc_pause_stats,
    "gc-memory-stats": cmd_gc_memory_stats,
    "gc-object-stats": cmd_gc_object_stats,
    "gc-phase-stats": cmd_gc_phase_stats,
    "gc-vm-options": cmd_gc_vm_options,
    "gc-details": cmd_gc_details,
    # Heap Dump
    "heap-report": cmd_heap_report,
    "heap-details": cmd_heap_details,
    "heap-biggest-objects": cmd_heap_biggest_objects,
    "heap-leak-report": cmd_heap_leak_report,
    "heap-threads": cmd_heap_threads,
    "heap-histogram": cmd_heap_histogram,
    "heap-dominator-tree": cmd_heap_dominator_tree,
    "heap-gc-roots": cmd_heap_gc_roots,
    "heap-system-properties": cmd_heap_system_properties,
    "heap-duplicated-classes": cmd_heap_duplicated_classes,
    # Heap Dump Interactive
    "heap-outbounds": cmd_heap_outbounds,
    "heap-inbounds": cmd_heap_inbounds,
    "heap-path-to-gc-roots": cmd_heap_path_to_gc_roots,
    "heap-inspector": cmd_heap_inspector,
    "heap-dominator-tree-children": cmd_heap_dominator_tree_children,
    "heap-merge-path-to-gc-roots": cmd_heap_merge_path_to_gc_roots,
    "heap-class-ref-objects": cmd_heap_class_ref_objects,
    # Thread Dump
    "thread-report": cmd_thread_report,
    "thread-overview": cmd_thread_overview,
    "thread-list": cmd_thread_list,
    "thread-monitors": cmd_thread_monitors,
    "thread-raw-content": cmd_thread_raw_content,
    "thread-call-site-tree": cmd_thread_call_site_tree,
    "thread-threads-of-group": cmd_thread_threads_of_group,
    "thread-by-monitor": cmd_thread_by_monitor,
    "thread-content": cmd_thread_content,
    # JFR
    "jfr-report": cmd_jfr_report,
    "jfr-metadata": cmd_jfr_metadata,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handler = COMMAND_MAP.get(args.command)
    if handler:
        handler(args)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
