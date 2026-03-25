#!/usr/bin/env python3
"""
ES 性能采集结果查询客户端

通过 MCP 接口查询 ES 集群的性能采集结果（firemap、heapdump、jstack、hotthread、task 等），
并支持将 COS 链接转换为可访问的 HTTPS 预签名链接。

子命令列表：
  query       查询 ES 集群性能采集结果（需指定 --start-time 和 --end-time）
  cos-sign    将 COS 链接转换为 HTTPS 预签名下载链接（需指定 --region-id）

环境变量：
  TCO_ES_MCP_TOKEN   MCP 接口鉴权 token

示例：
  # 查询 es-xxx 集群指定时间范围的 firemap 采集结果
  python es_profiling_client.py query --cluster-id es-xxx --item firemap \
      --start-time "2026-03-25 10:00:00" --end-time "2026-03-25 10:30:00"

  # 查询 es-xxx 集群指定时间范围的所有采集结果
  python es_profiling_client.py query --cluster-id es-xxx \
      --start-time "2026-03-25 10:00:00" --end-time "2026-03-25 10:30:00"

  # 将 COS 链接转为可下载的 HTTPS 链接（regionId 由 LLM 根据 cos_region_mapping.md 查表获得）
  python es_profiling_client.py cos-sign --cos-url "cos://bucket.cos.ap-guangzhou.myqcloud.com/path/file" --region-id 1
"""

import argparse
import json
import os
import sys
import uuid
import time
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

# ─── 常量配置 ───────────────────────────────────────────────────────────────────

API_BASE_MCP = "http://11.150.215.66:8080/xops/es/mcp"
TCO_ES_MCP_TOKEN = os.environ.get("TCO_ES_MCP_TOKEN", "es_mcp@2026")

DEFAULT_REGION_ID = -98
DEFAULT_USERNAME = "OpsAgent"
REQUEST_TIMEOUT = 50  # 请求超时（秒）

VALID_ITEMS = ("firemap", "jstack", "http", "hotthread", "task", "heapdump")


# ─── 工具函数 ───────────────────────────────────────────────────────────────────

def generate_request_id() -> str:
    return str(uuid.uuid4())


def generate_timestamp() -> int:
    return int(time.time() * 1000)


# ─── MCP API 请求 ──────────────────────────────────────────────────────────────

def make_mcp_request(
    interface: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    发送 MCP 请求到 ES MCP 服务

    Args:
        interface: MCP 接口名称（如 "query_es_firemap"、"create_cos_pre_sign_link"）
                   注意：query_es_firemap 是 MCP 端遗留名称，实际涵盖所有性能采集项
        params: 接口特定的业务参数

    Returns:
        API 响应的 JSON 数据
    """
    if not interface or not isinstance(interface, str):
        return {"retcode": -1, "message": "Error: interface 必须是非空字符串"}

    request_body = {
        "regionId": DEFAULT_REGION_ID,
        "username": DEFAULT_USERNAME,
        "requestId": generate_request_id(),
        "timestamp": generate_timestamp(),
        "interface": interface,
    }

    if params and isinstance(params, dict):
        request_body.update(params)

    mcp_rpc_body = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/call",
        "params": {
            "name": interface,
            "arguments": request_body,
        },
    }

    req = urllib.request.Request(
        API_BASE_MCP,
        data=json.dumps(mcp_rpc_body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TCO_ES_MCP_TOKEN}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            response_data = response.read().decode("utf-8")
            if not response_data:
                return {"retcode": -1, "message": "Error: 服务端返回空响应"}
            resp_json = json.loads(response_data)
            # JSON-RPC 响应解包
            if isinstance(resp_json, dict) and resp_json.get("jsonrpc") == "2.0":
                if "result" in resp_json:
                    result = resp_json["result"]
                    if isinstance(result, dict) and "content" in result:
                        content = result["content"]
                        if isinstance(content, list) and len(content) > 0:
                            text_data = content[0].get("text", "")
                            try:
                                return json.loads(text_data)
                            except json.JSONDecodeError:
                                return {"retcode": 0, "data": text_data}
                    return result
                if "error" in resp_json:
                    error_info = resp_json["error"]
                    if isinstance(error_info, dict):
                        return {
                            "retcode": -1,
                            "message": f"JSON-RPC Error: {error_info.get('message', 'Unknown error')}",
                            "error": error_info.get("data") or error_info,
                        }
                    return {"retcode": -1, "message": f"JSON-RPC Error: {error_info}"}
            return resp_json
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return {
            "retcode": -1,
            "message": f"HTTP Error {e.code}: {e.reason}",
            "error": error_body or str(e),
        }
    except urllib.error.URLError as e:
        return {"retcode": -1, "message": f"URL Error: {e.reason}", "error": str(e)}
    except TimeoutError:
        return {"retcode": -1, "message": f"Error: 请求超时 ({REQUEST_TIMEOUT}s)"}
    except json.JSONDecodeError as e:
        return {"retcode": -1, "message": f"JSON 解析错误: {e}", "error": str(e)}
    except Exception as e:
        return {"retcode": -1, "message": f"请求异常: {e}", "error": str(e)}


# ─── 业务接口 ───────────────────────────────────────────────────────────────────

def query_profiling(
    cluster_id: str,
    item: str = "",
    start_time: str = "",
    end_time: str = "",
    limit: int = 10,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    查询 ES 集群性能采集结果

    Args:
        cluster_id: ES 集群 ID，形如 es-xxx（必填）
        item: 采集项过滤，可选 firemap/jstack/http/hotthread/task/heapdump，空字符串表示查询所有
        start_time: 开始时间，格式 "YYYY-MM-DD HH:mm:ss"（必填）
        end_time: 结束时间，格式 "YYYY-MM-DD HH:mm:ss"（必填）
        limit: 分页大小，默认 10
        offset: 分页偏移量，默认 0

    Returns:
        API 响应，data 中包含采集结果列表
    """
    if not cluster_id:
        return {"retcode": -1, "message": "Error: cluster_id (集群 ID) 为必填参数，形如 es-xxx"}
    if not start_time:
        return {"retcode": -1, "message": "Error: start-time 为必填参数，格式 YYYY-MM-DD HH:mm:ss"}
    if not end_time:
        return {"retcode": -1, "message": "Error: end-time 为必填参数，格式 YYYY-MM-DD HH:mm:ss"}

    params = {
        "condition": cluster_id,
        "startTime": start_time,
        "endTime": end_time,
        "limit": limit,
        "offset": offset,
    }
    if item:
        params["item"] = item

    # MCP 端接口名为 query_es_firemap（遗留名称，实际支持所有采集项）
    return make_mcp_request("query_es_firemap", params)


def create_cos_presign_link(cos_url: str, region_id: int) -> Dict[str, Any]:
    """
    将 COS 链接转换为可访问的 HTTPS 预签名链接

    Args:
        cos_url: COS 文件链接，如 cos://bucket.cos.ap-guangzhou.myqcloud.com/path/to/file
        region_id: 地域 ID，需由调用方根据 COS URL 中的地域信息查表获得

    Returns:
        API 响应，data 中包含 HTTPS 预签名下载链接
    """
    if not cos_url:
        return {"retcode": -1, "message": "Error: cos_url 为必填参数"}
    if region_id is None:
        return {"retcode": -1, "message": "Error: region-id 为必填参数，请根据 COS URL 中的地域信息查表获得（见 references/cos_region_mapping.md）"}

    params = {
        "filename": cos_url,
        "regionId": region_id,
    }
    return make_mcp_request("create_cos_pre_sign_link", params)


# ─── argparse 子命令处理 ────────────────────────────────────────────────────────

def cmd_query(args: argparse.Namespace) -> Dict[str, Any]:
    """处理 query 子命令"""
    return query_profiling(
        cluster_id=args.cluster_id,
        item=args.item,
        start_time=args.start_time,
        end_time=args.end_time,
        limit=args.limit,
        offset=args.offset,
    )


def cmd_cos_sign(args: argparse.Namespace) -> Dict[str, Any]:
    """处理 cos-sign 子命令"""
    return create_cos_presign_link(
        cos_url=args.cos_url,
        region_id=args.region_id,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="es_profiling_client.py",
        description="ES 性能采集结果查询客户端 - 支持查询 firemap/heapdump/jstack 等并转换 COS 链接",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  # 查询 es-xxx 集群指定时间范围的 firemap\n"
            '  python es_profiling_client.py query --cluster-id es-xxx --item firemap \\\n'
            '      --start-time "2026-03-25 10:00:00" --end-time "2026-03-25 10:30:00"\n\n'
            "  # COS 链接转为 HTTPS 下载链接\n"
            '  python es_profiling_client.py cos-sign --cos-url "cos://bucket.cos.ap-guangzhou.myqcloud.com/path/file" --region-id 1\n'
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="可用子命令",
        description="使用 <子命令> -h 查看各命令的详细参数说明",
    )

    # ── query 子命令 ──
    p_query = subparsers.add_parser(
        "query",
        help="查询 ES 集群性能采集结果",
        description=(
            "查询指定 ES 集群的性能采集结果，支持按采集项和时间范围过滤。\n"
            "采集项包括：firemap、jstack、http、hotthread、task、heapdump。\n"
            "不指定采集项则查询所有。start-time 和 end-time 为必填参数。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            '  python es_profiling_client.py query --cluster-id es-xxx --item firemap \\\n'
            '      --start-time "2026-03-25 10:00:00" --end-time "2026-03-25 10:30:00"\n'
            '  python es_profiling_client.py query --cluster-id es-xxx \\\n'
            '      --start-time "2026-03-25 10:00:00" --end-time "2026-03-25 11:00:00"\n'
            '  python es_profiling_client.py query --cluster-id es-xxx --item heapdump \\\n'
            '      --start-time "2026-03-25 10:00:00" --end-time "2026-03-25 12:00:00"'
        ),
    )
    p_query.add_argument(
        "--cluster-id", type=str, required=True,
        help="ES 集群 ID，形如 es-xxx（必填）",
    )
    p_query.add_argument(
        "--item", type=str, default="", choices=["", *VALID_ITEMS],
        help="采集项过滤：firemap/jstack/http/hotthread/task/heapdump，不指定则查询所有",
    )
    p_query.add_argument(
        "--start-time", type=str, required=True,
        help='开始时间，格式 "YYYY-MM-DD HH:mm:ss"（必填）',
    )
    p_query.add_argument(
        "--end-time", type=str, required=True,
        help='结束时间，格式 "YYYY-MM-DD HH:mm:ss"（必填）',
    )
    p_query.add_argument(
        "--limit", type=int, default=10,
        help="分页大小（默认 10）",
    )
    p_query.add_argument(
        "--offset", type=int, default=0,
        help="分页偏移量（默认 0）",
    )
    p_query.set_defaults(func=cmd_query)

    # ── cos-sign 子命令 ──
    p_cos = subparsers.add_parser(
        "cos-sign",
        help="将 COS 链接转换为 HTTPS 预签名下载链接",
        description=(
            "将 COS 文件链接转换为可直接访问的 HTTPS 预签名链接（有效期 60 分钟）。\n"
            "region-id 为必填参数，需根据 COS URL 中的地域信息查表获得（见 references/cos_region_mapping.md）。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            '  python es_profiling_client.py cos-sign --cos-url "cos://bucket.cos.ap-guangzhou.myqcloud.com/path/file" --region-id 1\n'
            '  python es_profiling_client.py cos-sign --cos-url "cos://bucket.cos.ap-beijing.myqcloud.com/file" --region-id 8'
        ),
    )
    p_cos.add_argument(
        "--cos-url", type=str, required=True,
        help="COS 文件链接（必填）",
    )
    p_cos.add_argument(
        "--region-id", type=int, required=True,
        help="地域 ID（必填），需根据 COS URL 中 .cos.<region>.myqcloud.com 的 <region> 部分查表获得",
    )
    p_cos.set_defaults(func=cmd_cos_sign)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        result = args.func(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"retcode": -1, "message": f"Error: {e}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
