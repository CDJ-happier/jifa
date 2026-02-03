#!/bin/bash
# Jifa 启动脚本
# 此脚本应该放在 /data/jifa/start-jifa.sh

set -e

# Java 环境配置
# 重要: 必须使用系统级 Java，确保 jifa 用户可以访问
JAVA_HOME="/opt/java17-jifa"
export PATH="$JAVA_HOME/bin:$PATH"

# 应用目录
APP_HOME="/data/jifa/app/jifa"
APP_JAR="${APP_HOME}/lib/jifa.jar"

# 数据和配置目录
DATA_DIR="/data/jifa/storage"
LOG_DIR="/data/jifa/logs"
CONFIG_FILE="/data/jifa/config/application.yml"

# 确保目录存在
mkdir -p "${DATA_DIR}"
mkdir -p "${LOG_DIR}"

# JVM 参数 - 针对 72C256G 服务器优化
JVM_OPTS="-Xmx180g"
JVM_OPTS="${JVM_OPTS} -Xms180g"
JVM_OPTS="${JVM_OPTS} -XX:+UseG1GC"
JVM_OPTS="${JVM_OPTS} -XX:MaxGCPauseMillis=200"
JVM_OPTS="${JVM_OPTS} -XX:G1HeapRegionSize=32m"
JVM_OPTS="${JVM_OPTS} -XX:ParallelGCThreads=36"
JVM_OPTS="${JVM_OPTS} -XX:ConcGCThreads=12"
JVM_OPTS="${JVM_OPTS} -XX:G1ReservePercent=15"
JVM_OPTS="${JVM_OPTS} -XX:InitiatingHeapOccupancyPercent=45"
JVM_OPTS="${JVM_OPTS} -XX:+UnlockExperimentalVMOptions"
JVM_OPTS="${JVM_OPTS} -XX:+UseNUMA"
JVM_OPTS="${JVM_OPTS} -XX:+UseLargePages"
JVM_OPTS="${JVM_OPTS} -XX:+AlwaysPreTouch"
JVM_OPTS="${JVM_OPTS} -XX:+UseStringDeduplication"

# GC 日志配置
JVM_OPTS="${JVM_OPTS} -Xlog:gc*:file=${LOG_DIR}/gc.log:time,uptime,level,tags:filecount=10,filesize=100M"

# 应用必需的 JVM 参数
JVM_OPTS="${JVM_OPTS} --add-opens=java.base/java.lang=ALL-UNNAMED"
JVM_OPTS="${JVM_OPTS} --add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED"
JVM_OPTS="${JVM_OPTS} -Djdk.util.zip.disableZip64ExtraFieldValidation=true"

# 应用参数
APP_OPTS="--jifa.role=standalone-worker"
APP_OPTS="${APP_OPTS} --jifa.port=8102"
APP_OPTS="${APP_OPTS} --jifa.storage-path=${DATA_DIR}"

# Spring 配置文件
if [ -f "${CONFIG_FILE}" ]; then
    APP_OPTS="${APP_OPTS} --spring.config.additional-location=file:${CONFIG_FILE}"
fi

# 设置工作目录
cd "${APP_HOME}"

# 启动应用
echo "Starting Jifa..."
echo "APP_HOME: ${APP_HOME}"
echo "APP_JAR: ${APP_JAR}"
echo "DATA_DIR: ${DATA_DIR}"
echo "LOG_DIR: ${LOG_DIR}"
echo "CONFIG_FILE: ${CONFIG_FILE}"
echo ""

exec java ${JVM_OPTS} -jar "${APP_JAR}" ${APP_OPTS}
