#!/bin/bash
# Jifa 部署验证脚本
# 执行: bash verify.sh

set -e

echo "======================================"
echo "Jifa 部署验证"
echo "======================================"
echo ""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check_pass() {
    echo -e "${GREEN}✓ $1${NC}"
    PASS=$((PASS + 1))
}

check_fail() {
    echo -e "${RED}✗ $1${NC}"
    FAIL=$((FAIL + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# 1. 检查用户
echo "1. 检查 jifa 用户"
if id "jifa" &>/dev/null; then
    check_pass "用户 jifa 存在"
else
    check_fail "用户 jifa 不存在"
fi
echo ""

# 2. 检查目录
echo "2. 检查目录结构"
for dir in /data/jifa /data/jifa/storage /data/jifa/app /data/jifa/logs /data/jifa/config; do
    if [ -d "$dir" ]; then
        owner=$(stat -c '%U:%G' "$dir")
        if [ "$owner" = "jifa:jifa" ]; then
            check_pass "目录 $dir 存在且权限正确"
        else
            check_warn "目录 $dir 存在但所有者不是 jifa:jifa (当前: $owner)"
        fi
    else
        check_fail "目录 $dir 不存在"
    fi
done
echo ""

# 3. 检查应用文件
echo "3. 检查应用文件"
if [ -f "/data/jifa/app/jifa/lib/jifa.jar" ]; then
    check_pass "应用 jar 文件存在"
else
    check_fail "应用 jar 文件不存在"
fi

if [ -f "/data/jifa/start-jifa.sh" ]; then
    if [ -x "/data/jifa/start-jifa.sh" ]; then
        check_pass "启动脚本存在且可执行"
    else
        check_warn "启动脚本存在但不可执行"
    fi
else
    check_fail "启动脚本不存在"
fi
echo ""

# 4. 检查配置文件
echo "4. 检查配置文件"
if [ -f "/data/jifa/config/application.yml" ]; then
    check_pass "配置文件存在"

    # 检查配置内容
    if grep -q "max-file-size: 128GB" /data/jifa/config/application.yml; then
        check_pass "文件大小限制配置正确 (128GB)"
    else
        check_warn "文件大小限制可能未正确配置"
    fi

    if grep -q "storage-path: /data/jifa/storage" /data/jifa/config/application.yml; then
        check_pass "存储路径配置正确"
    else
        check_warn "存储路径可能未正确配置"
    fi
else
    check_fail "配置文件不存在"
fi
echo ""

# 5. 检查 systemd 服务
echo "5. 检查 systemd 服务"
if [ -f "/etc/systemd/system/jifa.service" ]; then
    check_pass "systemd 服务文件存在"

    if systemctl is-enabled jifa &>/dev/null; then
        check_pass "服务已启用（开机自启）"
    else
        check_warn "服务未启用"
    fi
else
    check_fail "systemd 服务文件不存在"
fi
echo ""

# 6. 检查服务状态
echo "6. 检查服务运行状态"
if systemctl is-active jifa &>/dev/null; then
    check_pass "服务正在运行"

    # 检查端口监听
    if sudo netstat -tlnp 2>/dev/null | grep -q ":8102" || sudo ss -tlnp 2>/dev/null | grep -q ":8102"; then
        check_pass "端口 8102 正在监听"
    else
        check_warn "端口 8102 未监听"
    fi

    # 检查进程
    if pgrep -u jifa java >/dev/null; then
        check_pass "Java 进程正在运行"

        # 显示内存使用
        pid=$(pgrep -u jifa java | head -1)
        mem=$(ps -p $pid -o rss= | awk '{printf "%.2f GB", $1/1024/1024}')
        echo "  内存使用: $mem"
    else
        check_warn "未找到 Java 进程"
    fi
else
    check_warn "服务未运行"
fi
echo ""

# 7. 检查 Java 环境
echo "7. 检查 Java 环境"
if [ -d "/home/jifa/.sdkman/candidates/java/current" ]; then
    check_pass "jifa 用户的 Java 环境存在"
    java_version=$(sudo -u jifa /home/jifa/.sdkman/candidates/java/current/bin/java -version 2>&1 | head -1)
    echo "  Java 版本: $java_version"
elif command -v java &>/dev/null; then
    check_pass "系统 Java 可用"
    java -version 2>&1 | head -3 | while read line; do echo "  $line"; done
else
    check_fail "未找到 Java"
fi
echo ""

# 8. 检查磁盘空间
echo "8. 检查磁盘空间"
disk_usage=$(df -h /data | tail -1 | awk '{print $5}' | sed 's/%//')
disk_avail=$(df -h /data | tail -1 | awk '{print $4}')
if [ "$disk_usage" -lt 80 ]; then
    check_pass "磁盘空间充足 (已用: ${disk_usage}%, 可用: ${disk_avail})"
elif [ "$disk_usage" -lt 90 ]; then
    check_warn "磁盘空间不足 (已用: ${disk_usage}%, 可用: ${disk_avail})"
else
    check_fail "磁盘空间严重不足 (已用: ${disk_usage}%, 可用: ${disk_avail})"
fi
echo ""

# 9. 测试 HTTP 访问
echo "9. 测试 HTTP 访问"
if systemctl is-active jifa &>/dev/null; then
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8102 | grep -q "200\|302\|404"; then
        check_pass "HTTP 服务可访问"
    else
        check_warn "HTTP 服务无响应（服务可能还在启动中）"
    fi
else
    check_warn "服务未运行，跳过 HTTP 测试"
fi
echo ""

# 10. 检查日志
echo "10. 检查日志文件"
if [ -f "/data/jifa/logs/jifa.log" ]; then
    log_size=$(du -h /data/jifa/logs/jifa.log | awk '{print $1}')
    check_pass "日志文件存在 (大小: $log_size)"

    echo "  最近的日志:"
    tail -5 /data/jifa/logs/jifa.log 2>/dev/null | sed 's/^/    /'
else
    check_warn "日志文件尚未生成（如果刚启动是正常的）"
fi
echo ""

# 总结
echo "======================================"
echo "验证总结"
echo "======================================"
echo -e "${GREEN}通过: $PASS${NC}"
if [ $FAIL -gt 0 ]; then
    echo -e "${RED}失败: $FAIL${NC}"
fi
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ 所有关键检查通过！${NC}"
    echo ""
    echo "后续操作:"
    echo "  1. 查看实时日志: sudo journalctl -u jifa -f"
    echo "  2. 访问服务: http://$(hostname -I | awk '{print $1}'):8102"
    echo "  3. 查看服务状态: sudo systemctl status jifa"
else
    echo -e "${RED}✗ 发现问题，请检查失败的项目${NC}"
    echo ""
    echo "故障排查:"
    echo "  1. 查看服务日志: sudo journalctl -u jifa -n 100"
    echo "  2. 查看应用日志: sudo tail -f /data/jifa/logs/jifa.log"
    echo "  3. 检查服务状态: sudo systemctl status jifa"
    exit 1
fi
