# Jifa 配置优先级说明

## 问题

启动脚本 (`start-jifa.sh`) 和配置文件 (`application.yml`) 中都有相同的配置，哪个会生效？

## Spring Boot 配置优先级

从**高到低**的优先级：

1. **命令行参数** (`--property=value`)
2. **外部配置文件** (`--spring.config.additional-location=file:...`)
3. **jar 包内的 application.yml**

**规则**：同一个属性，高优先级会覆盖低优先级。

## 当前配置分析

### 启动命令
```bash
java -jar jifa.jar \
  --jifa.role=standalone-worker \
  --jifa.port=8080 \                    # 命令行参数（高优先级）
  --jifa.storage-path=/data/jifa/storage \   # 命令行参数（高优先级）
  --spring.config.additional-location=file:/data/jifa/config/application.yml
```

### 配置文件 (/data/jifa/config/application.yml)
```yaml
jifa:
  role: standalone-worker
  storage-path: /data/jifa/storage     # 被命令行参数覆盖（实际不生效）

server:
  port: 8080                            # 被命令行 --jifa.port 映射，实际生效

spring:
  servlet:
    multipart:
      max-file-size: 128GB              # ✅ 生效（命令行没有指定）
      max-request-size: 128GB           # ✅ 生效（命令行没有指定）
```

## 配置生效情况

| 配置项 | 命令行 | application.yml | 实际生效 | 说明 |
|--------|--------|-----------------|----------|------|
| jifa.port | 8080 | 8080 (server.port) | 8080 | 命令行优先 |
| jifa.storage-path | /data/jifa/storage | /data/jifa/storage | /data/jifa/storage | 命令行优先 |
| max-file-size | ❌ | 128GB | ✅ 128GB | 仅在配置文件 |
| max-request-size | ❌ | 128GB | ✅ 128GB | 仅在配置文件 |
| tomcat.threads.max | ❌ | 500 | ✅ 500 | 仅在配置文件 |
| logging.file.name | ❌ | /data/jifa/logs/jifa.log | ✅ | 仅在配置文件 |

## ✅ application.yml 确实生效了！

虽然部分配置被命令行参数覆盖，但以下重要配置来自 application.yml：

1. **128GB 文件上传限制** ✅
2. **日志配置** ✅
3. **Tomcat 线程池配置** ✅
4. **JPA 配置** ✅

## 如何验证配置是否生效

### 方法1: 检查应用日志
```bash
# 查看启动日志，看加载的配置文件
sudo journalctl -u jifa | grep -i "config\|property"

# 查看应用日志中的配置信息
sudo tail -100 /data/jifa/logs/jifa.log | grep -E "max-file-size|port"
```

### 方法2: 查看实际效果
```bash
# 检查端口（应该是配置的端口）
sudo netstat -tlnp | grep java

# 尝试上传大文件（测试 128GB 限制）
# 上传小于 128GB 的文件应该成功
```

### 方法3: 添加日志验证
修改 `/data/jifa/config/application.yml`，添加一个独特的配置：
```yaml
logging:
  level:
    root: INFO
    org.eclipse.jifa: DEBUG  # 改为 DEBUG 看日志是否变化
```
重启服务后检查日志级别是否改变。

## 最佳实践建议

### 方案1: 命令行参数优先（当前方案）
- **优点**: 脚本清晰，一眼看出关键参数
- **缺点**: 命令行和配置文件有重复

**当前 start-jifa.sh**:
```bash
APP_OPTS="--jifa.role=standalone-worker"
APP_OPTS="${APP_OPTS} --jifa.port=8080"
APP_OPTS="${APP_OPTS} --jifa.storage-path=${DATA_DIR}"
```

### 方案2: 完全依赖配置文件（推荐）
- **优点**: 配置集中在一个文件，易于管理
- **缺点**: 需要读配置文件才知道参数

**修改后的 start-jifa.sh**:
```bash
# 仅指定配置文件，不覆盖任何参数
APP_OPTS=""
if [ -f "${CONFIG_FILE}" ]; then
    APP_OPTS="--spring.config.additional-location=file:${CONFIG_FILE}"
fi
```

**所有配置都在 application.yml**:
```yaml
jifa:
  role: standalone-worker
  port: 8080                    # 从这里读取
  storage-path: /data/jifa/storage  # 从这里读取
```

### 方案3: 混合模式（灵活）
- 关键参数（端口、路径）放命令行
- 详细配置（线程数、超时等）放配置文件

## 当前建议

**保持当前方案即可**，因为：

1. ✅ `application.yml` 中的 128GB 上传限制已经生效
2. ✅ 其他详细配置（日志、Tomcat、JPA）都生效
3. ✅ 命令行参数只覆盖了少数核心配置（端口、路径）
4. ✅ 两个地方的配置值是一致的，不会产生混淆

## 如果需要修改配置

### 修改端口
有两个地方需要同步修改（保持一致）：
1. `/data/jifa/start-jifa.sh` 第50行：`--jifa.port=8080`
2. `/data/jifa/config/application.yml` 第35行：`port: 8080`

修改后重启：
```bash
sudo systemctl restart jifa
```

### 修改文件上传限制
只需修改一个地方：
1. `/data/jifa/config/application.yml` 中的 `max-file-size` 和 `max-request-size`

修改后重启即可生效。

### 验证新配置
```bash
# 重启服务
sudo systemctl restart jifa

# 等待启动完成（约10秒）
sleep 10

# 检查端口
sudo netstat -tlnp | grep java

# 查看日志确认配置
sudo journalctl -u jifa -n 50
```

## 总结

- ✅ **application.yml 确实生效了**
- ✅ **128GB 上传限制来自 application.yml**
- ✅ 命令行参数只覆盖了少数配置（port, storage-path）
- ✅ 当前配置方式是合理的
- ⚠️ 如需修改端口，需要两个地方同步修改
