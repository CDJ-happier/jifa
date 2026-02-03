# 自动化脚本修复说明

## 问题

脚本在执行时卡住，原因是函数内部的 `log_*` 输出被捕获到了返回值中。

## 原因

Bash 中，函数的返回值通过 `echo` 输出，而 `$(function_name)` 会捕获**所有**输出，包括 `log_info` 等日志函数的输出。

**问题代码示例**:
```bash
upload_file() {
    log_info "上传中..."  # 这会被捕获到 transfer_id
    echo "$transfer_id"
}

transfer_id=$(upload_file "$url")  # transfer_id 包含了日志输出
```

## 解决方案

将所有日志输出重定向到 `stderr` (文件描述符 2)，只保留真正的返回值输出到 `stdout`。

**修复后的代码**:
```bash
upload_file() {
    log_info "上传中..." >&2  # 重定向到 stderr
    echo "$transfer_id"        # 只有这个输出到 stdout
}

transfer_id=$(upload_file "$url")  # 现在 transfer_id 只包含数字
```

## 修复的函数

✅ `upload_file()`
✅ `wait_for_transfer()`
✅ `get_file_unique_name()`
✅ `trigger_analysis()`
✅ `wait_for_analysis()`
✅ `get_analysis_summary()`

## 测试结果

脚本现在可以正常运行，输出示例：

```
[INFO] ==========================================
[INFO] Jifa 自动 Heap Dump 分析
[INFO] ==========================================

[INFO] 检查 Jifa 服务连接...
[SUCCESS] Jifa 服务连接正常

[INFO] 步骤1: 发起文件上传...
[SUCCESS] 文件上传已发起，Transfer ID: 10

[INFO] 步骤2: 等待文件上传完成...
[INFO]   上传进度: 55% (183.49M / 332.74M)
[SUCCESS] 文件上传完成！
[INFO]   File ID: 6

[INFO] 步骤3: 获取文件信息...
[SUCCESS] 文件信息获取成功
[INFO]   Unique Name: c05c5257-184b-4e33-b8b5-3278893fc729

[INFO] 步骤4: 触发 heap dump 分析...
[SUCCESS] Heap dump 分析已启动

[INFO] 步骤5: 等待分析完成...
[INFO]   分析进度: 70.0% - Parsing heap dump...
[INFO]   分析进度: 84.0% - Extracting objects...
```

## 使用方法

```bash
bash /opt/jifa/scripts/auto-analyze-heap-dump.sh "YOUR_COS_URL"
```

**注意**:
- 分析大文件（300MB+）可能需要几分钟到十几分钟
- 脚本会实时显示进度，不要中断
- 默认超时时间: 3600 秒（1 小时）

---

**修复时间**: 2026-02-03
**修复状态**: ✅ 已完成
