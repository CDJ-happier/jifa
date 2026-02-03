# Eclipse Jifa项目配置汇总文档

## 📋 项目概述

Eclipse Jifa是一个用于分析Java应用程序性能数据的工具，支持GC日志、堆转储、JFR文件等多种分析类型。本文档汇总了所有配置修改、Docker构建和部署指南。

## 🔧 已完成的配置修改

### 1. 128GB大文件上传配置

#### application.yml配置修改
```yaml
spring:
  servlet:
    multipart:
      max-request-size: 128GB    # 修改前: 512MB
      max-file-size: 128GB       # 修改前: 512MB

jifa:
  storage-path: /data/jifa-storage  # 建议使用数据盘而非系统盘
```

#### HttpConfigurer.java配置修改
```java
@Bean
TomcatServletWebServerFactory tomcatServletWebServerFactory() {
    TomcatServletWebServerFactory tomcatServletWebServerFactory = new TomcatServletWebServerFactory();
    tomcatServletWebServerFactory.addConnectorCustomizers(connector -> {
        connector.setAsyncTimeout(-1);
        // 设置最大POST大小以支持128GB文件上传
        connector.setMaxPostSize(137438953472L); // 128GB in bytes
        connector.setMaxSwallowSize(137438953472L); // 128GB in bytes
    });
    return tomcatServletWebServerFactory;
}
```

### 2. 关键配置参数对比

| 配置项 | 作用 | 默认值 | 修改后值 |
|--------|------|--------|----------|
| `max-file-size` | 单个文件最大大小 | 512MB | 128GB |
| `max-request-size` | 整个请求最大大小 | 512MB | 128GB |
| `maxPostSize` | Tomcat POST请求最大大小 | 2MB | 128GB |
| `maxSwallowSize` | Tomcat吞入数据最大大小 | 2MB | 128GB |

## 🐳 Docker构建配置

### 1. Dockerfile结构

项目包含三个Dockerfile文件：

#### 主Dockerfile
```dockerfile
FROM node:18 AS build
RUN apt-get update && apt-get install openjdk-17-jdk -y
WORKDIR /workspace/
COPY . /workspace/
RUN --mount=type=cache,target=/root/.gradle ./gradlew clean build -x test
RUN mkdir -p server/build/dependency && (cd server/build/dependency; jar -xf ../libs/jifa.jar)

FROM eclipse-temurin:17-jdk
VOLUME /tmp
ARG DEPENDENCY=/workspace/server/build/dependency
COPY --from=build ${DEPENDENCY}/BOOT-INF/lib /jifa/lib
COPY --from=build ${DEPENDENCY}/META-INF /jifa/META-INF
COPY --from=build ${DEPENDENCY}/BOOT-INF/classes /jifa
EXPOSE 8102
ENTRYPOINT ["java","--add-opens=java.base/java.lang=ALL-UNNAMED","--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED","-Djdk.util.zip.disableZip64ExtraFieldValidation=true","-cp","jifa:jifa/lib/*","org.eclipse.jifa.server.Launcher"]
```

#### build.Dockerfile（构建阶段）
```dockerfile
FROM node:18
RUN apt-get update \
    && apt-get install openjdk-17-jdk -y \
    && apt-get clean
WORKDIR /workspace/
COPY . /workspace/
ARG GRADLE_ARGS
RUN --mount=type=cache,target=/root/.gradle eval set -- "$GRADLE_ARGS" &&  ./gradlew $@
RUN mkdir -p server/build/dependency && (cd server/build/dependency; jar -xf ../libs/jifa.jar)
```

#### final.Dockerfile（最终镜像）
```dockerfile
FROM eclipse-temurin:17-jdk
VOLUME /tmp
ARG TARGETARCH
COPY jifa-build/$TARGETARCH/BOOT-INF/lib /jifa/lib
COPY jifa-build/$TARGETARCH/META-INF /jifa/META-INF
COPY jifa-build/$TARGETARCH/BOOT-INF/classes /jifa
ENTRYPOINT ["java","--add-opens=java.base/java.lang=ALL-UNNAMED","--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED","-Djdk.util.zip.disableZip64ExtraFieldValidation=true","-cp","jifa:jifa/lib/*","org.eclipse.jifa.server.Launcher"]
```

### 2. GitHub Actions构建配置

```yaml
name: Build and Push Docker Image
on: workflow_dispatch

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - id: read-version
        run: |
          version=$(head -n 1 version)
          echo "::set-output name=version::$version"
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME}}
          password: ${{ secrets.DOCKER_PASSWORD}}
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64
          push: true
          tags: eclipsejifa/jifa:${{ steps.read-version.outputs.version }}
```

## 🚀 启动命令和部署

### 1. 使用jifa.sh脚本启动

```bash
# 基本启动
./jifa.sh

# 指定端口
./jifa.sh -p 8102

# 指定镜像标签
./jifa.sh -t latest

# 设置JVM参数
./jifa.sh --jvm-options "-Xmx64g -Xms32g"

# 上传文件分析
./jifa.sh /path/to/heapdump.hprof
```

### 2. 直接Docker命令启动

```bash
# 基本启动
docker run -p 8102:8102 eclipsejifa/jifa:latest

# 使用数据盘挂载
docker run -p 8102:8102 -v /data/jifa-storage:/jifa-storage eclipsejifa/jifa:latest

# 设置JVM参数
docker run -p 8102:8102 -e JDK_JAVA_OPTIONS="-Xmx64g -Xms32g" eclipsejifa/jifa:latest

# 完整配置示例
docker run -d \
  --name jifa \
  -p 8102:8102 \
  -v /data/jifa-storage:/jifa-storage \
  -e JDK_JAVA_OPTIONS="-Xmx64g -Xms32g -XX:+UseG1GC" \
  eclipsejifa/jifa:latest
```

### 3. Kubernetes集群部署

使用cluster.yml文件进行Kubernetes部署：

```bash
# 创建命名空间和资源
kubectl apply -f cluster.yml

# 查看部署状态
kubectl get pods -n jifa

# 查看服务
kubectl get svc -n jifa
```

## ⚙️ 服务器配置建议

### 1. 硬件配置（针对72c256G分析机）

```yaml
# 推荐配置
CPU: 72核心
内存: 256GB RAM
磁盘: 1TB NVMe SSD（数据盘）
网络: 万兆网络

# JVM参数优化
-Xmx128g -Xms64g                    # 堆内存设置
-XX:MaxMetaspaceSize=4g            # 元空间大小
-XX:+UseG1GC                       # 使用G1垃圾回收器
-XX:MaxGCPauseMillis=200           # 最大GC暂停时间
-XX:ParallelGCThreads=16           # 并行GC线程数
```

### 2. 存储配置

```bash
# 挂载数据盘到/data目录
mount /dev/sdb1 /data

# 创建Jifa存储目录
mkdir -p /data/jifa-storage
chmod 755 /data/jifa-storage
```

## 🔒 安全性配置

### 1. Docker安全配置

```bash
# 使用非root用户运行
docker run --user 1000:1000 eclipsejifa/jifa:latest

# 限制资源使用
docker run --memory=128g --cpus=32 eclipsejifa/jifa:latest

# 只读文件系统
docker run --read-only -v /data/jifa-storage:/jifa-storage eclipsejifa/jifa:latest
```

### 2. 网络安全性

```bash
# 使用内部网络
docker run --network=internal eclipsejifa/jifa:latest

# 限制端口暴露
docker run -p 127.0.0.1:8102:8102 eclipsejifa/jifa:latest
```

## 📊 监控和维护

### 1. 日志监控

```bash
# 查看容器日志
docker logs jifa-container

# 实时日志监控
docker logs -f jifa-container

# 日志文件位置
/jifa-storage/logs/application.log
```

### 2. 性能监控

```bash
# 容器资源使用
docker stats jifa-container

# 磁盘空间监控
df -h /data/jifa-storage

# 内存使用监控
free -h
```

### 3. 文件清理策略

```bash
# 定期清理脚本示例（cron任务）
0 2 * * * find /data/jifa-storage -name "*.hprof" -mtime +30 -delete
0 3 * * * find /data/jifa-storage -name "*.jfr" -mtime +30 -delete
```

## 🛠️ 故障排除

### 常见问题解决方案

1. **文件上传失败：文件过大**
   - 检查所有128GB配置是否生效
   - 验证Tomcat和Spring配置

2. **内存不足**
   - 增加JVM堆内存设置
   - 检查系统内存使用情况

3. **磁盘空间不足**
   - 定期清理过期文件
   - 扩展数据盘容量

4. **网络超时**
   - 调整客户端超时设置
   - 检查网络带宽

## 📞 技术支持

### 验证配置是否生效

```bash
# 检查Spring配置
docker exec jifa-container cat /jifa/application.yml | grep multipart

# 检查启动日志
docker logs jifa-container | grep -i "tomcat\|multipart"

# 测试文件上传
curl -X POST -F "file=@test.hprof" http://localhost:8102/jifa-api/files/upload
```

### 联系支持

- 项目文档：查看项目README文件
- 问题反馈：通过GitHub Issues
- 社区支持：Eclipse社区论坛

---

**文档版本**: 1.0  
**最后更新**: 2026-02-03  
**适用版本**: Eclipse Jifa最新版本