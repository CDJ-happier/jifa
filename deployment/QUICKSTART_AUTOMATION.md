# Jifa 自动化分析快速指南

## 概述

本指南介绍如何使用自动化脚本快速完成 heap dump 文件的上传和分析。

---

## 方式一：使用自动化脚本（推荐）

### 1. 脚本位置

```bash
/opt/jifa/scripts/auto-analyze-heap-dump.sh
```

### 2. 使用方法

```bash
bash /opt/jifa/scripts/auto-analyze-heap-dump.sh "https://example.com/dump.hprof"
```

### 3. 环境变量

```bash
# 自定义 Jifa 服务地址
export JIFA_HOST="21.6.180.85"
export JIFA_PORT="8080"

bash /opt/jifa/scripts/auto-analyze-heap-dump.sh "https://example.com/dump.hprof"
```

### 4. 脚本功能

✅ 自动上传文件
✅ 实时显示上传进度
✅ 自动触发分析
✅ 实时显示分析进度
✅ 输出分析结果和访问链接

### 5. 输出示例

```
[INFO] ==========================================
[INFO] Jifa 自动 Heap Dump 分析
[INFO] ==========================================

[INFO] 检查 Jifa 服务连接...
[SUCCESS] Jifa 服务连接正常

[INFO] 步骤1: 发起文件上传...
[INFO] URL: https://example.com/dump.hprof
[SUCCESS] 文件上传已发起，Transfer ID: 2

[INFO] 步骤2: 等待文件上传完成...
[INFO]   上传进度: 41% (162.32 MB / 393.05 MB)
[INFO]   上传进度: 78% (306.54 MB / 393.05 MB)
[SUCCESS] 文件上传完成！
[INFO]   文件大小: 393.05 MB
[INFO]   File ID: 1

[INFO] 步骤3: 获取文件信息...
[SUCCESS] 文件信息获取成功
[INFO]   Unique Name: 497dda82-542e-416c-8d5c-352eb252dbbe
[INFO]   原始文件名: dump.hprof

[INFO] 步骤4: 触发 heap dump 分析...
[SUCCESS] Heap dump 分析已启动

[INFO] 步骤5: 等待分析完成...
[INFO]   分析进度: 15% - Building dominator tree...
[INFO]   分析进度: 45% - Computing retained sizes...
[INFO]   分析进度: 80% - Building indexes...
[SUCCESS] Heap dump 分析完成！

[INFO] 步骤6: 获取分析结果...
[SUCCESS] 分析结果获取成功

==========================================
Heap Dump 分析结果概览
==========================================
{
  "heapSize": 393046228,
  "objectCount": 1234567,
  "classCount": 5678,
  ...
}

[SUCCESS] ==========================================
[SUCCESS] 分析完成！可以通过以下方式访问：
[SUCCESS] ==========================================

Web UI:
  http://21.6.180.85:8080/#/heap/497dda82-542e-416c-8d5c-352eb252dbbe

API 示例:
  # 获取详细信息
  curl -X POST 'http://21.6.180.85:8080/jifa-api/analysis' ...

[INFO] File ID: 1
[INFO] Unique Name: 497dda82-542e-416c-8d5c-352eb252dbbe
```

---

## 方式二：手动执行（逐步）

如果需要更细粒度的控制，可以手动执行各个步骤。

### 步骤 1: 上传文件

```bash
TRANSFER_ID=$(curl -s -X POST http://localhost:8080/jifa-api/files/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "type": "HEAP_DUMP",
    "method": "URL",
    "url": "https://example.com/dump.hprof"
  }')

echo "Transfer ID: $TRANSFER_ID"
```

### 步骤 2: 查询上传进度

```bash
while true; do
  RESPONSE=$(curl -s "http://localhost:8080/jifa-api/files/transfer/$TRANSFER_ID")
  STATE=$(echo "$RESPONSE" | jq -r '.state')

  if [ "$STATE" = "SUCCESS" ]; then
    FILE_ID=$(echo "$RESPONSE" | jq -r '.fileId')
    echo "上传完成，File ID: $FILE_ID"
    break
  elif [ "$STATE" = "FAILED" ]; then
    echo "上传失败"
    exit 1
  fi

  echo "上传中... $RESPONSE"
  sleep 5
done
```

### 步骤 3: 获取文件 uniqueName

```bash
RESPONSE=$(curl -s -G http://localhost:8080/jifa-api/files \
  --data-urlencode "type=HEAP_DUMP" \
  --data-urlencode "page=1" \
  --data-urlencode "pageSize=25")

UNIQUE_NAME=$(echo "$RESPONSE" | jq -r ".data[] | select(.id == $FILE_ID) | .uniqueName")
echo "Unique Name: $UNIQUE_NAME"
```

### 步骤 4: 触发分析

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d "{
    \"namespace\": \"heap-dump\",
    \"api\": \"analyze\",
    \"target\": \"$UNIQUE_NAME\",
    \"parameters\": {}
  }"
```

### 步骤 5: 查询分析进度

```bash
while true; do
  RESPONSE=$(curl -s -X POST http://localhost:8080/jifa-api/analysis \
    -H "Content-Type: application/json" \
    -d "{
      \"namespace\": \"heap-dump\",
      \"api\": \"progressOfAnalysis\",
      \"target\": \"$UNIQUE_NAME\"
    }")

  STATE=$(echo "$RESPONSE" | jq -r '.state')

  if [ "$STATE" = "SUCCESS" ]; then
    echo "分析完成！"
    break
  elif [ "$STATE" = "FAILED" ]; then
    echo "分析失败"
    exit 1
  fi

  PERCENT=$(echo "$RESPONSE" | jq -r '.percent // 0')
  MESSAGE=$(echo "$RESPONSE" | jq -r '.message // "分析中..."')
  echo "分析进度: $(echo "$PERCENT * 100" | bc)% - $MESSAGE"

  sleep 5
done
```

### 步骤 6: 获取分析结果

```bash
# 获取概览
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d "{
    \"namespace\": \"heap-dump\",
    \"api\": \"getDetails\",
    \"target\": \"$UNIQUE_NAME\"
  }" | jq .

# 获取最大对象
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d "{
    \"namespace\": \"heap-dump\",
    \"api\": \"getBiggestObjects\",
    \"target\": \"$UNIQUE_NAME\",
    \"parameters\": {\"page\": 1, \"pageSize\": 10}
  }" | jq .

# 获取泄漏报告
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d "{
    \"namespace\": \"heap-dump\",
    \"api\": \"getLeakReport\",
    \"target\": \"$UNIQUE_NAME\"
  }" | jq .
```

---

## 方式三：集成到 Go 后端

### 1. Go 代码示例

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "time"
)

const (
    JifaBaseURL = "http://21.6.180.85:8080/jifa-api"
)

// 上传文件
func uploadFile(dumpURL string) (int, error) {
    payload := map[string]string{
        "type":   "HEAP_DUMP",
        "method": "URL",
        "url":    dumpURL,
    }

    jsonData, _ := json.Marshal(payload)
    resp, err := http.Post(
        JifaBaseURL+"/files/transfer",
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    if err != nil {
        return 0, err
    }
    defer resp.Body.Close()

    body, _ := io.ReadAll(resp.Body)
    var transferID int
    fmt.Sscanf(string(body), "%d", &transferID)

    return transferID, nil
}

// 等待上传完成
func waitForTransfer(transferID int) (int, error) {
    for {
        resp, err := http.Get(fmt.Sprintf("%s/files/transfer/%d", JifaBaseURL, transferID))
        if err != nil {
            return 0, err
        }

        var result map[string]interface{}
        json.NewDecoder(resp.Body).Decode(&result)
        resp.Body.Close()

        state := result["state"].(string)
        if state == "SUCCESS" {
            fileID := int(result["fileId"].(float64))
            return fileID, nil
        } else if state == "FAILED" {
            return 0, fmt.Errorf("upload failed")
        }

        time.Sleep(5 * time.Second)
    }
}

// 获取 uniqueName
func getUniqueName(fileID int) (string, error) {
    resp, err := http.Get(fmt.Sprintf(
        "%s/files?type=HEAP_DUMP&page=1&pageSize=25",
        JifaBaseURL,
    ))
    if err != nil {
        return "", err
    }
    defer resp.Body.Close()

    var result struct {
        Data []struct {
            ID         int    `json:"id"`
            UniqueName string `json:"uniqueName"`
        } `json:"data"`
    }
    json.NewDecoder(resp.Body).Decode(&result)

    for _, file := range result.Data {
        if file.ID == fileID {
            return file.UniqueName, nil
        }
    }

    return "", fmt.Errorf("file not found")
}

// 触发分析
func triggerAnalysis(uniqueName string) error {
    payload := map[string]interface{}{
        "namespace":  "heap-dump",
        "api":        "analyze",
        "target":     uniqueName,
        "parameters": map[string]interface{}{},
    }

    jsonData, _ := json.Marshal(payload)
    _, err := http.Post(
        JifaBaseURL+"/analysis",
        "application/json",
        bytes.NewBuffer(jsonData),
    )

    return err
}

// 等待分析完成
func waitForAnalysis(uniqueName string) error {
    for {
        payload := map[string]interface{}{
            "namespace": "heap-dump",
            "api":       "progressOfAnalysis",
            "target":    uniqueName,
        }

        jsonData, _ := json.Marshal(payload)
        resp, err := http.Post(
            JifaBaseURL+"/analysis",
            "application/json",
            bytes.NewBuffer(jsonData),
        )
        if err != nil {
            return err
        }

        var result map[string]interface{}
        json.NewDecoder(resp.Body).Decode(&result)
        resp.Body.Close()

        state := result["state"].(string)
        if state == "SUCCESS" {
            return nil
        } else if state == "FAILED" {
            return fmt.Errorf("analysis failed")
        }

        time.Sleep(5 * time.Second)
    }
}

// 主流程
func analyzeHeapDump(dumpURL string) (string, error) {
    // 1. 上传文件
    transferID, err := uploadFile(dumpURL)
    if err != nil {
        return "", err
    }
    fmt.Printf("Transfer ID: %d\n", transferID)

    // 2. 等待上传完成
    fileID, err := waitForTransfer(transferID)
    if err != nil {
        return "", err
    }
    fmt.Printf("File ID: %d\n", fileID)

    // 3. 获取 uniqueName
    uniqueName, err := getUniqueName(fileID)
    if err != nil {
        return "", err
    }
    fmt.Printf("Unique Name: %s\n", uniqueName)

    // 4. 触发分析
    if err := triggerAnalysis(uniqueName); err != nil {
        return "", err
    }

    // 5. 等待分析完成
    if err := waitForAnalysis(uniqueName); err != nil {
        return "", err
    }

    // 6. 返回 Web UI 链接
    webURL := fmt.Sprintf("http://21.6.180.85:8080/#/heap/%s", uniqueName)
    return webURL, nil
}

func main() {
    dumpURL := "https://example.com/dump.hprof"
    webURL, err := analyzeHeapDump(dumpURL)
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }

    fmt.Printf("分析完成！访问链接: %s\n", webURL)
}
```

### 2. Shell 脚本集成

如果 Go 后端可以执行 shell 脚本，可以直接调用：

```go
import (
    "os/exec"
    "fmt"
)

func analyzeHeapDump(dumpURL string) (string, error) {
    cmd := exec.Command(
        "bash",
        "/opt/jifa/scripts/auto-analyze-heap-dump.sh",
        dumpURL,
    )

    // 设置环境变量
    cmd.Env = append(os.Environ(),
        "JIFA_HOST=21.6.180.85",
        "JIFA_PORT=8080",
    )

    output, err := cmd.CombinedOutput()
    if err != nil {
        return "", fmt.Errorf("script failed: %v\n%s", err, output)
    }

    // 从输出中提取 uniqueName 和 Web URL
    // ... 解析输出 ...

    return webURL, nil
}
```

---

## 常见 API 使用示例

### 1. 获取最大对象

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getBiggestObjects",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "page": 1,
      "pageSize": 10
    }
  }' | jq .
```

### 2. 获取内存泄漏报告

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getLeakReport",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe"
  }' | jq .
```

### 3. 执行 OQL 查询

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getOQLResult",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "oql": "select * from java.lang.String s where s.value.length > 1000",
      "page": 1,
      "pageSize": 50
    }
  }' | jq .
```

### 4. 获取直方图

```bash
curl -X POST http://localhost:8080/jifa-api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "heap-dump",
    "api": "getHistogram",
    "target": "497dda82-542e-416c-8d5c-352eb252dbbe",
    "parameters": {
      "groupBy": "BY_CLASS",
      "page": 1,
      "pageSize": 50,
      "sortBy": "RETAINED_SIZE",
      "ascendingOrder": false
    }
  }' | jq .
```

---

## 故障排查

### 问题1: jq 命令未找到

```bash
sudo yum install -y jq
```

### 问题2: 脚本权限不足

```bash
chmod +x /opt/jifa/scripts/auto-analyze-heap-dump.sh
```

### 问题3: 无法连接到 Jifa 服务

检查服务状态：
```bash
sudo systemctl status jifa
```

检查端口监听：
```bash
sudo netstat -tlnp | grep 8080
```

### 问题4: 上传超时

增加超时时间：
```bash
# 编辑脚本，修改 MAX_WAIT 变量
MAX_WAIT=7200  # 2 小时
```

---

## 更多信息

- **完整 API 文档**: [API_REFERENCE.md](API_REFERENCE.md)
- **部署文档**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **配置说明**: [CONFIGURATION_PRIORITY.md](CONFIGURATION_PRIORITY.md)

---

**版本**: 1.0
**更新时间**: 2026-02-03
