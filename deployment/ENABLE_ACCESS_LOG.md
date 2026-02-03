# 启用 Jifa HTTP 访问日志

## 问题

为什么 `/data/jifa/logs/jifa.log` 中看不到 HTTP 请求日志（GET、POST、DELETE 等）？

## 原因

Spring Boot 默认**不记录 HTTP 访问日志**，只记录应用事件和错误。

- ✅ 错误会被记录（如 404、500 错误）
- ❌ 正常的 HTTP 请求不会被记录

## 解决方案：启用 Tomcat 访问日志

编辑配置文件 `/data/jifa/config/application.yml`，在 `server.tomcat` 部分添加 `accesslog` 配置：

```yaml
server:
  port: 8080
  tomcat:
    threads:
      max: 500
      min-spare: 50
    max-connections: 1000
    accept-count: 1000
    relaxed-query-chars:
      - '['
      - ']'
    # ========== 添加以下配置 ==========
    accesslog:
      enabled: true
      directory: /data/jifa/logs
      prefix: access_log
      suffix: .log
      pattern: '%h %l %u %t "%r" %s %b %D'
      # 日志格式说明：
      # %h - 客户端 IP 地址
      # %l - 远程逻辑用户名（通常是 -）
      # %u - 认证用户名
      # %t - 时间戳
      # %r - 请求行（方法 URL 协议）
      # %s - HTTP 状态码
      # %b - 响应字节数（不包括 HTTP 头）
      # %D - 请求处理时间（毫秒）
```

## 操作步骤

### 1. 编辑配置文件

```bash
sudo vim /data/jifa/config/application.yml
```

在 `server.tomcat` 部分添加上述 `accesslog` 配置。

### 2. 重启 Jifa 服务

```bash
sudo systemctl restart jifa
```

### 3. 验证配置生效

```bash
# 查看日志文件
ls -lh /data/jifa/logs/

# 应该看到新的访问日志文件
# access_log.2026-02-03.log
```

### 4. 测试访问日志

```bash
# 发起一个测试请求
curl -s http://localhost:8080/jifa-api/files?type=HEAP_DUMP\&page=1\&pageSize=1 > /dev/null

# 查看访问日志
tail -f /data/jifa/logs/access_log.$(date +%Y-%m-%d).log
```

## 访问日志示例

启用后，访问日志格式如下：

```
127.0.0.1 - - [03/Feb/2026:21:50:15 +0800] "GET /jifa-api/files?type=HEAP_DUMP&page=1&pageSize=1 HTTP/1.1" 200 245 152
127.0.0.1 - - [03/Feb/2026:21:51:20 +0800] "DELETE /jifa-api/files/16 HTTP/1.1" 200 0 89
127.0.0.1 - - [03/Feb/2026:21:52:30 +0800] "POST /jifa-api/analysis HTTP/1.1" 200 1234 3456
```

字段说明：
- `127.0.0.1` - 客户端 IP
- `[03/Feb/2026:21:50:15 +0800]` - 时间戳
- `"GET /jifa-api/files?..."` - 请求方法和 URL
- `200` - HTTP 状态码
- `245` - 响应字节数
- `152` - 处理时间（毫秒）

## 访问日志 vs 应用日志

### 应用日志 (jifa.log)
- **内容**: 应用事件、错误、调试信息
- **级别**: INFO、WARN、ERROR
- **用途**: 诊断应用问题、查看错误堆栈

示例：
```
2026-02-03T21:26:35.454+08:00  INFO 1855968 --- [main] org.eclipse.jifa.server.Launcher : Started Launcher in 9.126 seconds
2026-02-03T21:39:08.863+08:00 ERROR 1855968 --- [http-nio-8080-exec-22] o.e.j.s.c.GlobalExceptionHandler : Error occurred when handling http request '/actuator/health'
```

### 访问日志 (access_log.YYYY-MM-DD.log)
- **内容**: 每个 HTTP 请求
- **格式**: 类似 Apache/Nginx 访问日志
- **用途**: 流量分析、性能监控、审计

示例：
```
127.0.0.1 - - [03/Feb/2026:21:50:15 +0800] "GET /jifa-api/files?type=HEAP_DUMP&page=1&pageSize=1 HTTP/1.1" 200 245 152
127.0.0.1 - - [03/Feb/2026:21:51:20 +0800] "DELETE /jifa-api/files/16 HTTP/1.1" 200 0 89
```

## 日志轮转

访问日志会自动按天切割：
```
access_log.2026-02-03.log
access_log.2026-02-04.log
access_log.2026-02-05.log
```

### 配置日志保留天数

如果需要限制访问日志的保留时间，可以添加：

```yaml
server:
  tomcat:
    accesslog:
      enabled: true
      directory: /data/jifa/logs
      prefix: access_log
      suffix: .log
      pattern: '%h %l %u %t "%r" %s %b %D'
      max-days: 30  # 保留 30 天
```

或者使用 logrotate 管理：

```bash
sudo vim /etc/logrotate.d/jifa-access

# 添加以下内容：
/data/jifa/logs/access_log.*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    create 0644 jifa jifa
}
```

## 性能影响

启用访问日志会有轻微的性能影响：
- 写入磁盘 I/O
- 每个请求增加约 0.1-1ms 延迟

对于大多数场景，这个影响可以忽略不计。

## 自定义日志格式

如果需要更详细的信息，可以修改 `pattern`：

```yaml
# 包含更多信息
pattern: '%h %l %u %t "%r" %s %b %D %{Referer}i %{User-Agent}i'

# 常用模式变量：
# %a - 远程 IP 地址
# %A - 本地 IP 地址
# %b - 响应字节数（CLF 格式）
# %B - 响应字节数
# %D - 请求处理时间（毫秒）
# %F - 响应提交时间（毫秒）
# %h - 远程主机名
# %H - 请求协议
# %m - 请求方法
# %p - 本地端口
# %q - 查询字符串（带 ? 前缀）
# %r - 请求行
# %s - HTTP 状态码
# %S - 用户 session ID
# %t - 时间戳
# %T - 请求处理时间（秒）
# %u - 远程用户
# %U - 请求 URI
# %v - 本地服务器名
# %{xxx}i - 请求头 xxx
# %{xxx}o - 响应头 xxx
```

## 查看访问日志

```bash
# 实时查看
tail -f /data/jifa/logs/access_log.$(date +%Y-%m-%d).log

# 查看今天的所有请求
cat /data/jifa/logs/access_log.$(date +%Y-%m-%d).log

# 统计请求方法
awk '{print $6}' /data/jifa/logs/access_log.*.log | sort | uniq -c

# 统计状态码
awk '{print $9}' /data/jifa/logs/access_log.*.log | sort | uniq -c

# 查找慢请求（> 1000ms）
awk '$NF > 1000 {print $0}' /data/jifa/logs/access_log.*.log

# 统计访问最多的 IP
awk '{print $1}' /data/jifa/logs/access_log.*.log | sort | uniq -c | sort -rn | head -10
```

## 总结

**为什么之前看不到请求日志？**
- Spring Boot 默认不记录 HTTP 访问日志
- 只有错误会被记录到 `jifa.log`

**启用访问日志后的效果**：
- ✅ 所有 HTTP 请求都会被记录
- ✅ 可以看到 GET、POST、DELETE 等请求
- ✅ 可以分析流量、性能、审计

**推荐配置**：
- 启用访问日志（用于审计和监控）
- 保留 30 天
- 使用默认格式（性能最佳）

---

**相关文档**:
- [配置优先级](CONFIGURATION_PRIORITY.md)
- [部署指南](DEPLOYMENT.md)

**版本**: 1.0
**更新时间**: 2026-02-03
