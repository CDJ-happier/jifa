# Java 环境配置说明

## 问题背景

systemd 以 `jifa` 用户身份运行服务时，无法访问其他用户（如 jasondjcai）的 Java 环境（如 SDKMAN 安装的 Java）。

## 解决方案

将 Java 安装到系统级目录，所有用户都可以访问。

### 步骤 1: 准备 Java 环境

**方法 A: 从现有安装复制（推荐）**

如果你已经有 Java 17（例如通过 SDKMAN 安装），可以复制到系统目录：

```bash
# 复制 Java 到系统目录
sudo cp -r ~/.sdkman/candidates/java/17.0.18-kona /opt/java17-jifa

# 设置所有者和权限
sudo chown -R root:root /opt/java17-jifa
sudo chmod -R 755 /opt/java17-jifa

# 验证
/opt/java17-jifa/bin/java -version
```

**方法 B: 系统包管理器安装**

```bash
# CentOS/RHEL
sudo yum install java-17-openjdk-devel
# Java 会安装到 /usr/lib/jvm/

# Ubuntu/Debian
sudo apt install openjdk-17-jdk
# Java 会安装到 /usr/lib/jvm/
```

### 步骤 2: 配置启动脚本

在 `/data/jifa/start-jifa.sh` 开头添加：

```bash
# Java 环境配置
JAVA_HOME="/opt/java17-jifa"
export PATH="$JAVA_HOME/bin:$PATH"
```

### 步骤 3: 验证 jifa 用户可以访问 Java

```bash
# 测试 jifa 用户能否执行 Java
sudo -u jifa /opt/java17-jifa/bin/java -version
```

如果能正常输出 Java 版本信息，说明配置正确。

## 为什么不在 systemd 中配置？

虽然可以在 systemd 服务文件中通过 `Environment` 设置 `JAVA_HOME` 和 `PATH`，但：

1. **脚本中直接调用 `java`**: `start-jifa.sh` 脚本最后使用 `exec java`，需要在脚本执行环境中能找到 `java` 命令
2. **环境变量继承问题**: systemd 的环境变量不一定完全传递到 bash 脚本中
3. **可维护性**: 在启动脚本中明确配置 Java 路径更清晰，便于排查问题

## 最佳实践

推荐配置方式（已在部署脚本中实现）：

1. **系统级 Java**: 安装在 `/opt/java17-jifa`
2. **启动脚本配置**: 在 `start-jifa.sh` 开头设置 `JAVA_HOME` 和 `PATH`
3. **systemd 作为补充**: 同时在 systemd 服务文件中配置（双保险）

这样确保无论从何处启动（手动、systemd、其他方式），都能找到正确的 Java。

## 故障排查

如果服务启动失败，提示 "java: not found"：

```bash
# 1. 检查 Java 是否存在
ls -la /opt/java17-jifa/bin/java

# 2. 检查权限
sudo -u jifa /opt/java17-jifa/bin/java -version

# 3. 检查启动脚本
head -20 /data/jifa/start-jifa.sh

# 4. 查看详细日志
sudo journalctl -u jifa -n 50
```

## 目录权限要求

```
/opt/java17-jifa/
├── bin/
│   └── java           # 必须有执行权限 (755)
├── lib/
└── ...

所有者: root:root
权限: 755 (rwxr-xr-x)
```

确保 `other` 用户（包括 jifa）有读和执行权限。
