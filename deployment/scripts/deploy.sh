#!/bin/bash
# Jifa 自动化部署脚本
# 执行: sudo bash deploy.sh

set -e

echo "======================================"
echo "Jifa 生产环境部署脚本"
echo "======================================"
echo ""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用 sudo 运行此脚本${NC}"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "部署文件目录: ${SCRIPT_DIR}"

# 检查构建产物
BUILD_TAR="${SCRIPT_DIR}/../server/build/distributions/jifa.tar"
if [ ! -f "${BUILD_TAR}" ]; then
    echo -e "${RED}错误: 找不到构建产物 ${BUILD_TAR}${NC}"
    echo "请先运行: sudo bash jifa-jpackage.sh"
    exit 1
fi

echo -e "${GREEN}✓ 找到构建产物${NC}"
echo ""

# 步骤 1: 创建 jifa 用户
echo "步骤 1: 创建 jifa 用户"
if id "jifa" &>/dev/null; then
    echo -e "${YELLOW}用户 jifa 已存在，跳过创建${NC}"
else
    useradd -r -m -s /bin/bash jifa
    echo -e "${GREEN}✓ 用户 jifa 创建成功${NC}"
fi
echo ""

# 步骤 2: 创建目录结构
echo "步骤 2: 创建目录结构"
mkdir -p /data/jifa/storage/temp
mkdir -p /data/jifa/app
mkdir -p /data/jifa/logs
mkdir -p /data/jifa/config
chown -R jifa:jifa /data/jifa
echo -e "${GREEN}✓ 目录结构创建成功${NC}"
echo ""

# 步骤 3: 解压应用
echo "步骤 3: 解压应用到 /data/jifa/app"
if [ -d "/data/jifa/app/jifa" ]; then
    echo "备份现有应用..."
    mv /data/jifa/app/jifa /data/jifa/app/jifa.backup.$(date +%Y%m%d_%H%M%S)
fi
tar -xf "${BUILD_TAR}" -C /data/jifa/app
chown -R jifa:jifa /data/jifa/app
echo -e "${GREEN}✓ 应用解压成功${NC}"
echo ""

# 步骤 4: 复制配置文件
echo "步骤 4: 复制配置文件"
if [ ! -f "/data/jifa/config/application.yml" ]; then
    cp "${SCRIPT_DIR}/config/application-production.yml" /data/jifa/config/application.yml
    chown jifa:jifa /data/jifa/config/application.yml
    echo -e "${GREEN}✓ 配置文件已复制${NC}"
else
    echo -e "${YELLOW}配置文件已存在，跳过复制（如需更新请手动操作）${NC}"
fi
echo ""

# 步骤 5: 复制启动脚本
echo "步骤 5: 复制启动脚本"
cp "${SCRIPT_DIR}/scripts/start-jifa.sh" /data/jifa/start-jifa.sh
chmod +x /data/jifa/start-jifa.sh
chown jifa:jifa /data/jifa/start-jifa.sh
echo -e "${GREEN}✓ 启动脚本已复制${NC}"
echo ""

# 步骤 6: 配置 Java 环境
echo "步骤 6: 检查 Java 环境"
JIFA_JAVA=""
if [ -d "/home/jifa/.sdkman/candidates/java/current" ]; then
    JIFA_JAVA="/home/jifa/.sdkman/candidates/java/current"
    echo -e "${GREEN}✓ 使用 jifa 用户的 Java: ${JIFA_JAVA}${NC}"
elif [ -n "$JAVA_HOME" ]; then
    JIFA_JAVA="$JAVA_HOME"
    echo -e "${GREEN}✓ 使用系统 Java: ${JIFA_JAVA}${NC}"
else
    echo -e "${YELLOW}警告: 未找到 Java，systemd 服务可能无法启动${NC}"
    echo "请为 jifa 用户安装 Java 或设置 JAVA_HOME"
fi
echo ""

# 步骤 7: 安装 systemd 服务
echo "步骤 7: 安装 systemd 服务"
# 动态生成服务文件，设置正确的 JAVA_HOME
cat > /etc/systemd/system/jifa.service << EOF
[Unit]
Description=Jifa - Java Issues Finding Assistant
Documentation=https://eclipse-jifa.github.io/jifa/
After=network.target

[Service]
Type=simple
User=jifa
Group=jifa

WorkingDirectory=/data/jifa/app/jifa

ExecStart=/bin/bash /data/jifa/start-jifa.sh

TimeoutStopSec=60

Restart=on-failure
RestartSec=10

StandardOutput=journal
StandardError=journal

LimitNOFILE=65536
LimitNPROC=65536

NoNewPrivileges=true
PrivateTmp=true

EOF

# 添加 JAVA_HOME 环境变量（如果找到了）
if [ -n "$JIFA_JAVA" ]; then
    cat >> /etc/systemd/system/jifa.service << EOF
Environment="JAVA_HOME=${JIFA_JAVA}"
Environment="PATH=${JIFA_JAVA}/bin:/usr/local/bin:/usr/bin:/bin"

EOF
fi

cat >> /etc/systemd/system/jifa.service << EOF
[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ systemd 服务文件已创建${NC}"
echo ""

# 步骤 8: 重载 systemd
echo "步骤 8: 重载 systemd 配置"
systemctl daemon-reload
echo -e "${GREEN}✓ systemd 配置已重载${NC}"
echo ""

# 步骤 9: 启用服务
echo "步骤 9: 启用 jifa 服务（开机自启）"
systemctl enable jifa
echo -e "${GREEN}✓ jifa 服务已启用${NC}"
echo ""

# 完成
echo "======================================"
echo -e "${GREEN}部署完成！${NC}"
echo "======================================"
echo ""
echo "后续操作:"
echo "  1. 启动服务: sudo systemctl start jifa"
echo "  2. 查看状态: sudo systemctl status jifa"
echo "  3. 查看日志: sudo journalctl -u jifa -f"
echo "  4. 访问服务: http://$(hostname -I | awk '{print $1}'):8102"
echo ""
echo "服务管理命令:"
echo "  启动: sudo systemctl start jifa"
echo "  停止: sudo systemctl stop jifa"
echo "  重启: sudo systemctl restart jifa"
echo "  状态: sudo systemctl status jifa"
echo ""
echo "目录结构:"
echo "  应用根目录: /data/jifa/"
echo "  应用程序: /data/jifa/app/"
echo "  数据存储: /data/jifa/storage/"
echo "  日志文件: /data/jifa/logs/"
echo "  配置文件: /data/jifa/config/application.yml"
echo "  启动脚本: /data/jifa/start-jifa.sh"
echo "  systemd: /etc/systemd/system/jifa.service"
echo ""
