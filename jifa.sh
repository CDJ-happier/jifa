#!/bin/sh
# Copyright (c) 2023 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0
#
# SPDX-License-Identifier: EPL-2.0

set -eu

TAG="latest"
PORT="8102"
DATA_DIR="/data/jifa-storage"
MOUNTS=""
INPUT_FILES=""
INPUT_FILE_COUNT=0
JVM_OPTIONS=""

check_docker() {
  if ! command -v docker &>/dev/null; then
    echo "docker is not installed"
    exit 1
  fi
}

setup_data_dir() {
  if [ -z "$DATA_DIR" ]; then
    # 使用默认数据目录
    DATA_DIR="$HOME/jifa-storage"
    echo "Using default data directory: $DATA_DIR"
  fi
  
  # 创建数据目录（如果不存在）
  if [ ! -d "$DATA_DIR" ]; then
    echo "Creating data directory: $DATA_DIR"
    mkdir -p "$DATA_DIR"
  fi
  
  # 创建日志目录（如果不存在）
  LOGS_DIR="$DATA_DIR/logs"
  if [ ! -d "$LOGS_DIR" ]; then
    echo "Creating logs directory: $LOGS_DIR"
    mkdir -p "$LOGS_DIR"
  fi
  
  # 检查目录权限
  if [ ! -w "$DATA_DIR" ]; then
    echo "Error: Data directory $DATA_DIR is not writable"
    exit 1
  fi
  
  if [ ! -w "$LOGS_DIR" ]; then
    echo "Error: Logs directory $LOGS_DIR is not writable"
    exit 1
  fi
}

launch_jifa() {
  check_docker
  setup_data_dir
  
  # 添加数据目录挂载和配置
  DATA_MOUNT="-v $DATA_DIR:/jifa-storage"
  DATA_CONFIG="--jifa.storage-path=/jifa-storage"
  
  # 为72核256G服务器优化JVM配置（如果用户没有自定义JVM选项）
  if [ -z "$JVM_OPTIONS" ]; then
    JVM_OPTIONS="-Xmx180g -Xms180g -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:G1HeapRegionSize=32m -XX:ParallelGCThreads=36 -XX:ConcGCThreads=12 -XX:G1ReservePercent=15 -XX:InitiatingHeapOccupancyPercent=45 -Dspring.servlet.multipart.max-file-size=128GB -Dspring.servlet.multipart.max-request-size=128GB -XX:+UnlockExperimentalVMOptions -XX:+UseNUMA -XX:+UseLargePages -XX:+UseTransparentHugePages -XX:+AlwaysPreTouch -XX:+UseStringDeduplication -XX:+UseCompressedOops -XX:+UseCompressedClassPointers -Xlog:gc:file=/jifa-storage/logs/gc.log:time,level,tags"
  fi
  
  docker run --pull=always -e JDK_JAVA_OPTIONS="$JVM_OPTIONS" -p ${PORT}:${PORT} $DATA_MOUNT $MOUNTS eclipsejifa/jifa:${TAG} --jifa.port=${PORT} $DATA_CONFIG $INPUT_FILES
}

while [ $# -gt 0 ]; do
  case $1 in
  -t)
    TAG=$2
    shift
    ;;
  -p)
    PORT=$2
    shift
    ;;
  -d|--data-dir)
    DATA_DIR=$2
    shift
    ;;
  --jvm-options)
    JVM_OPTIONS=$2
    shift
    ;;
  *)
    ABSOLUTE_PATH=$(realpath "$1")
    if [ ! -f "$ABSOLUTE_PATH" ]; then
      echo "$1 does not exist or is not a regular file"
      exit 1
    fi

    FILE_NAME=$(basename "$ABSOLUTE_PATH")

    MOUNTS="$MOUNTS -v $ABSOLUTE_PATH:/input-file-$INPUT_FILE_COUNT/$FILE_NAME"
    INPUT_FILES="$INPUT_FILES --jifa.input-files[$INPUT_FILE_COUNT]=/input-file-$INPUT_FILE_COUNT/$FILE_NAME"
    INPUT_FILE_COUNT=$((INPUT_FILE_COUNT+1))
    ;;
  esac
  shift
done

launch_jifa
