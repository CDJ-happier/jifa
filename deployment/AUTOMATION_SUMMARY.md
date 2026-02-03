# Jifa Heap Dump 自动化分析方案总结

## 背景

用户需求：
1. Go 后端可以向节点下发脚本
2. 节点上的 dump 文件上传到 COS 后，获得下载 URL
3. 需要自动化流程：上传到 Jifa → 触发分析 → 获取结果

## 解决方案

已完成以下工作，提供三种集成方式：

---

## 方案一：Shell 脚本自动化（推荐）

### 1. 脚本位置
```
/opt/jifa/scripts/auto-analyze-heap-dump.sh
```

### 2. 使用方法
```bash
bash /opt/jifa/scripts/auto-analyze-heap-dump.sh "https://cos.example.com/dump.hprof"
```

### 3. 功能特性
- ✅ 完全自动化流程（上传 → 分析 → 结果）
- ✅ 实时进度显示
- ✅ 错误处理和重试
- ✅ 依赖检查（curl, jq）
- ✅ 服务健康检查
- ✅ 彩色输出，易于阅读
- ✅ 最终输出 Web UI 链接和 API 示例

### 4. 环境变量
```bash
export JIFA_HOST="21.6.180.85"
export JIFA_PORT="8080"
```

### 5. Go 后端集成示例
```go
import "os/exec"

func analyzeHeapDump(dumpURL string) (string, error) {
    cmd := exec.Command(
        "bash",
        "/opt/jifa/scripts/auto-analyze-heap-dump.sh",
        dumpURL,
    )
    cmd.Env = append(os.Environ(),
        "JIFA_HOST=21.6.180.85",
        "JIFA_PORT=8080",
    )
    output, err := cmd.CombinedOutput()
    // 解析输出获取 uniqueName 和 Web URL
    return webURL, err
}
```

### 6. 优点
- 简单易用，一行命令完成
- 无需修改 Go 代码，脚本独立维护
- 易于调试和测试
- 适合快速原型和临时任务

---

## 方案二：REST API 直接调用

### 1. API 流程

```
1. POST /jifa-api/files/transfer
   → 获取 transferId

2. 轮询 GET /jifa-api/files/transfer/{transferId}
   → 等待上传完成，获取 fileId

3. GET /jifa-api/files?type=HEAP_DUMP&page=1&pageSize=25
   → 根据 fileId 查找 uniqueName

4. POST /jifa-api/analysis
   → {"namespace":"heap-dump","api":"analyze","target":"{uniqueName}"}
   → 触发分析

5. 轮询 POST /jifa-api/analysis
   → {"namespace":"heap-dump","api":"progressOfAnalysis","target":"{uniqueName}"}
   → 等待分析完成

6. POST /jifa-api/analysis
   → {"namespace":"heap-dump","api":"getDetails","target":"{uniqueName}"}
   → 获取分析结果
```

### 2. Go 实现示例

参考 `/opt/jifa/deployment/QUICKSTART_AUTOMATION.md` 中的完整 Go 代码示例。

### 3. 优点
- 完全控制流程
- 可以集成到 Go 代码中
- 适合需要自定义逻辑的场景
- 可以获取详细的分析结果（不仅仅是 Web URL）

---

## 方案三：混合模式

### 1. 方式
- Go 后端负责上传文件到 Jifa
- 使用脚本进行后续分析

### 2. 实现
```go
// 1. Go 代码上传文件
transferID := uploadToJifa(dumpURL)
fileID := waitForTransfer(transferID)
uniqueName := getUniqueName(fileID)

// 2. 调用脚本进行分析（传入 uniqueName）
cmd := exec.Command(
    "bash",
    "/opt/jifa/scripts/analyze-only.sh",  // 只做分析的简化版本
    uniqueName,
)
output, err := cmd.CombinedOutput()
```

### 3. 优点
- 灵活性高
- Go 代码可以获取 fileId 等信息
- 脚本处理复杂的分析流程

---

## 关键 API 端点

### 文件管理
| API | 方法 | 用途 |
|-----|------|------|
| `/files/transfer` | POST | 从 URL 上传文件 |
| `/files/transfer/{id}` | GET | 查询上传进度 |
| `/files` | GET | 查询文件列表 |
| `/files/upload` | POST | 直接上传文件（multipart） |

### 分析管理
| API | namespace | api | 用途 |
|-----|-----------|-----|------|
| `/analysis` | heap-dump | analyze | 触发分析 |
| `/analysis` | heap-dump | progressOfAnalysis | 查询分析进度 |
| `/analysis` | heap-dump | getDetails | 获取概览信息 |
| `/analysis` | heap-dump | getBiggestObjects | 获取最大对象 |
| `/analysis` | heap-dump | getLeakReport | 获取泄漏报告 |
| `/analysis` | heap-dump | getHistogram | 获取直方图 |
| `/analysis` | heap-dump | getOQLResult | 执行 OQL 查询 |

完整 API 文档: `/opt/jifa/deployment/API_REFERENCE.md`

---

## Web UI 访问

分析完成后，可通过浏览器访问：
```
http://21.6.180.85:8080/#/heap/{uniqueName}
```

---

## 文件目录结构

```
/opt/jifa/
├── scripts/
│   └── auto-analyze-heap-dump.sh          # 自动化分析脚本 ⭐
│
└── deployment/
    ├── README_FIRST.txt                   # 快速开始
    ├── INDEX.md                           # 文档索引
    ├── QUICKSTART_AUTOMATION.md           # 自动化快速指南 🔥
    ├── API_REFERENCE.md                   # API 完整参考 📚
    ├── CONFIGURATION_PRIORITY.md          # 配置优先级说明
    ├── DEPLOYMENT.md                      # 完整部署文档
    └── SUMMARY.md                         # 部署总结
```

---

## 使用建议

### 开发/测试阶段
使用 **方案一（Shell 脚本）**:
- 快速验证流程
- 易于调试
- 无需修改 Go 代码

### 生产环境
根据需求选择：

**如果只需要 Web UI 链接**:
- 使用方案一（Shell 脚本）
- 简单可靠，维护成本低

**如果需要获取分析结果数据**:
- 使用方案二（REST API）
- 可以获取详细的分析数据
- 集成到监控/告警系统

**如果需要灵活控制**:
- 使用方案三（混合模式）
- 结合两者优点

---

## 测试验证

### 1. 测试自动化脚本

```bash
# 安装依赖
sudo yum install -y jq bc

# 测试脚本
bash /opt/jifa/scripts/auto-analyze-heap-dump.sh \
  "https://tco-qinge-gz-1303868265.cos.ap-guangzhou.myqcloud.com/upload/es-hir3378j/9.99.112.43/dump_jasondjcai_1769754421863.hprof?q-sign-algorithm=..."
```

### 2. 验证 API

```bash
# 测试上传
curl -X POST http://21.6.180.85:8080/jifa-api/files/transfer \
  -H "Content-Type: application/json" \
  -d '{"type":"HEAP_DUMP","method":"URL","url":"https://..."}'

# 测试查询文件列表
curl -G http://21.6.180.85:8080/jifa-api/files \
  --data-urlencode "type=HEAP_DUMP" \
  --data-urlencode "page=1" \
  --data-urlencode "pageSize=25"
```

---

## 常见问题

### Q1: Shell 脚本执行失败，提示 "jq: command not found"
```bash
sudo yum install -y jq bc
```

### Q2: 上传超时
编辑脚本，增加 `MAX_WAIT` 值：
```bash
MAX_WAIT=7200  # 2 小时
```

### Q3: 如何获取详细的分析结果（不仅仅是 Web URL）
使用方案二（REST API），调用各种分析 API，例如：
- `getBiggestObjects`: 获取最大对象
- `getLeakReport`: 获取泄漏报告
- `getHistogram`: 获取直方图

参考 API_REFERENCE.md 获取完整 API 列表。

### Q4: Go 后端如何解析脚本输出
脚本输出格式固定，可以通过正则提取关键信息：
```
File ID: 1
Unique Name: 497dda82-542e-416c-8d5c-352eb252dbbe
Web UI: http://21.6.180.85:8080/#/heap/497dda82-542e-416c-8d5c-352eb252dbbe
```

Go 解析示例：
```go
import "regexp"

func parseScriptOutput(output string) (fileID int, uniqueName, webURL string) {
    // 提取 File ID
    re := regexp.MustCompile(`File ID: (\d+)`)
    if matches := re.FindStringSubmatch(output); len(matches) > 1 {
        fmt.Sscanf(matches[1], "%d", &fileID)
    }

    // 提取 Unique Name
    re = regexp.MustCompile(`Unique Name: ([a-zA-Z0-9-]+)`)
    if matches := re.FindStringSubmatch(output); len(matches) > 1 {
        uniqueName = matches[1]
    }

    // 提取 Web URL
    re = regexp.MustCompile(`Web UI:\s+(http://[^\s]+)`)
    if matches := re.FindStringSubmatch(output); len(matches) > 1 {
        webURL = matches[1]
    }

    return
}
```

---

## 下一步

1. **测试脚本**:
   ```bash
   bash /opt/jifa/scripts/auto-analyze-heap-dump.sh "YOUR_COS_URL"
   ```

2. **集成到 Go 后端**:
   - 参考 `QUICKSTART_AUTOMATION.md` 中的 Go 代码示例
   - 选择合适的方案（Shell 脚本 / REST API / 混合模式）

3. **监控和告警**:
   - 分析完成后，可以通过 API 获取泄漏报告
   - 设置告警阈值（例如：堆内存使用率 > 80%）

4. **定期清理**:
   - 调用 `release` API 释放内存
   - 调用 `clean` API 清理磁盘缓存

---

## 联系方式

- **文档位置**: `/opt/jifa/deployment/`
- **脚本位置**: `/opt/jifa/scripts/`
- **部署目录**: `/data/jifa/`
- **服务管理**: `sudo systemctl {status|start|stop|restart} jifa`

---

**版本**: 1.0
**更新时间**: 2026-02-03
**作者**: Claude Code Internal
