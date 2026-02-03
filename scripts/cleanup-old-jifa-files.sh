#!/bin/bash

# ==========================================
# Jifa 文件自动清理脚本
# ==========================================
# 功能：删除超过指定天数的 heap dump 文件
# 使用：bash cleanup-old-files.sh [天数]
# 示例：bash cleanup-old-files.sh 7
# ==========================================

set -euo pipefail

# ==========================================
# 配置项
# ==========================================
JIFA_HOST="${JIFA_HOST:-localhost}"
JIFA_PORT="${JIFA_PORT:-8080}"
JIFA_BASE_URL="http://${JIFA_HOST}:${JIFA_PORT}/jifa-api"
DEFAULT_RETENTION_DAYS=7
DRY_RUN="${DRY_RUN:-false}"  # 设置为 true 时只显示将删除的文件，不实际删除

# ==========================================
# 颜色输出
# ==========================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# ==========================================
# 检查依赖
# ==========================================
check_dependencies() {
    local missing_deps=()

    for cmd in curl jq date; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "缺少必要的依赖: ${missing_deps[*]}"
        log_error "请安装: sudo yum install -y ${missing_deps[*]}"
        exit 1
    fi
}

# ==========================================
# 检查服务连接
# ==========================================
check_service() {
    log_info "检查 Jifa 服务连接 (${JIFA_BASE_URL})..." >&2

    local response
    response=$(curl -sf -G "${JIFA_BASE_URL}/files" \
        --data-urlencode "type=HEAP_DUMP" \
        --data-urlencode "page=1" \
        --data-urlencode "pageSize=1" 2>/dev/null)

    if [ $? -eq 0 ] && echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        log_success "Jifa 服务连接正常" >&2
        return 0
    fi

    log_error "无法连接到 Jifa 服务: ${JIFA_BASE_URL}" >&2
    log_error "请检查:" >&2
    log_error "  1. Jifa 服务是否运行: sudo systemctl status jifa" >&2
    log_error "  2. 端口是否正确: ${JIFA_PORT}" >&2
    log_error "  3. 防火墙设置" >&2
    exit 1
}

# ==========================================
# 获取文件列表
# ==========================================
get_files() {
    local page="$1"
    local page_size="$2"

    local response
    response=$(curl -s -G "${JIFA_BASE_URL}/files" \
        --data-urlencode "type=HEAP_DUMP" \
        --data-urlencode "page=${page}" \
        --data-urlencode "pageSize=${page_size}")

    if echo "$response" | jq -e '.errorCode' > /dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$response" | jq -r '.message')
        log_error "查询文件列表失败: $error_msg" >&2
        return 1
    fi

    echo "$response"
}

# ==========================================
# 删除文件
# ==========================================
delete_file() {
    local file_id="$1"
    local file_name="$2"
    local created_time="$3"

    if [ "$DRY_RUN" = "true" ]; then
        log_warn "[DRY-RUN] 将删除: ID=$file_id, 名称=$file_name, 创建时间=$created_time" >&2
        return 0
    fi

    local response
    response=$(curl -s -X DELETE "${JIFA_BASE_URL}/files/${file_id}" -w "\n%{http_code}")

    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 204 ]; then
        log_success "已删除: ID=$file_id, 名称=$file_name, 创建时间=$created_time" >&2
        return 0
    else
        log_error "删除失败: ID=$file_id, HTTP=$http_code, 响应=$body" >&2
        return 1
    fi
}

# ==========================================
# 计算文件年龄（天数）
# ==========================================
calculate_age_days() {
    local created_time="$1"

    # 将 ISO 8601 时间转换为 Unix 时间戳
    # 格式: 2026-01-27T10:30:45 或 2026-01-27T10:30:45.123
    local created_timestamp
    created_timestamp=$(date -d "${created_time}" +%s 2>/dev/null || echo "0")

    if [ "$created_timestamp" -eq 0 ]; then
        log_warn "无法解析时间: $created_time" >&2
        echo "0"
        return
    fi

    local current_timestamp
    current_timestamp=$(date +%s)

    local age_seconds=$((current_timestamp - created_timestamp))
    local age_days=$((age_seconds / 86400))

    echo "$age_days"
}

# ==========================================
# 主函数
# ==========================================
main() {
    local retention_days="${1:-$DEFAULT_RETENTION_DAYS}"

    log_info "==========================================" >&2
    log_info "Jifa 文件自动清理脚本" >&2
    log_info "==========================================" >&2
    log_info "保留天数: ${retention_days} 天" >&2
    log_info "删除超过 ${retention_days} 天的文件" >&2
    if [ "$DRY_RUN" = "true" ]; then
        log_warn "DRY-RUN 模式：不会实际删除文件" >&2
    fi
    log_info "==========================================" >&2
    echo "" >&2

    # 检查依赖
    check_dependencies

    # 检查服务
    check_service

    # 统计信息
    local total_files=0
    local deleted_count=0
    local failed_count=0
    local kept_count=0

    # 分页查询所有文件
    local page=1
    local page_size=100
    local has_more=true

    while [ "$has_more" = "true" ]; do
        log_info "查询第 $page 页文件（每页 $page_size 条）..." >&2

        local response
        response=$(get_files "$page" "$page_size")

        local total
        total=$(echo "$response" | jq -r '.totalSize // 0')

        local files
        files=$(echo "$response" | jq -c '.data[]')

        if [ -z "$files" ]; then
            log_info "第 $page 页无文件" >&2
            has_more=false
            break
        fi

        # 处理每个文件
        while IFS= read -r file; do
            total_files=$((total_files + 1))

            local file_id
            file_id=$(echo "$file" | jq -r '.id')
            local file_name
            file_name=$(echo "$file" | jq -r '.originalName')
            local unique_name
            unique_name=$(echo "$file" | jq -r '.uniqueName')
            local created_time
            created_time=$(echo "$file" | jq -r '.createdTime')
            local file_size
            file_size=$(echo "$file" | jq -r '.size')

            # 计算文件年龄
            local age_days
            age_days=$(calculate_age_days "$created_time")

            if [ "$age_days" -gt "$retention_days" ]; then
                log_info "文件过期: ID=$file_id, 年龄=${age_days}天, 名称=$file_name" >&2
                if delete_file "$file_id" "$file_name" "$created_time"; then
                    deleted_count=$((deleted_count + 1))
                else
                    failed_count=$((failed_count + 1))
                fi
            else
                log_info "文件保留: ID=$file_id, 年龄=${age_days}天, 名称=$file_name" >&2
                kept_count=$((kept_count + 1))
            fi
        done <<< "$files"

        # 检查是否还有更多页
        local total_pages
        total_pages=$(echo "$response" | jq -r '.totalPage // 0')

        if [ "$page" -ge "$total_pages" ]; then
            has_more=false
        else
            page=$((page + 1))
        fi
    done

    # 输出统计信息
    echo "" >&2
    log_info "==========================================" >&2
    log_info "清理完成" >&2
    log_info "==========================================" >&2
    log_info "总文件数: $total_files" >&2
    log_success "已删除: $deleted_count" >&2
    log_info "已保留: $kept_count" >&2
    if [ "$failed_count" -gt 0 ]; then
        log_error "删除失败: $failed_count" >&2
    fi
    log_info "==========================================" >&2
}

# ==========================================
# 使用说明
# ==========================================
usage() {
    cat <<EOF
用法: $0 [天数]

删除超过指定天数的 heap dump 文件。

参数:
  天数         保留文件的天数，默认为 7 天

环境变量:
  JIFA_HOST    Jifa 服务主机，默认 localhost
  JIFA_PORT    Jifa 服务端口，默认 8080
  DRY_RUN      设置为 true 时只显示将删除的文件，不实际删除

示例:
  # 删除超过 7 天的文件
  $0 7

  # 删除超过 30 天的文件
  $0 30

  # 使用自定义 Jifa 地址
  JIFA_HOST=21.6.180.85 JIFA_PORT=8080 $0 7

  # Dry-run 模式（不实际删除）
  DRY_RUN=true $0 7

定时任务配置（每天凌晨 2 点执行）:
  crontab -e
  0 2 * * * bash /opt/jifa/scripts/cleanup-old-files.sh 7 >> /var/log/jifa-cleanup.log 2>&1

EOF
}

# ==========================================
# 脚本入口
# ==========================================
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
fi

main "$@"
