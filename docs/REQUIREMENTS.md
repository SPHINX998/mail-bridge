# 部署前需要准备什么

这份清单面向公开仓库使用者。

目标：让使用者在开始前先判断自己是否适合部署这套系统。

## 一句话判断

如果你能接受：

- 自己配置 Gmail / Google Cloud
- 本地运行 Python 服务
- 本地运行 OpenClaw
- 使用 QQ Bot 作为通知面

那么你适合继续。

## 必需账号与服务

### 1. Gmail 账号

需要一个可接收新邮件事件的 Gmail 邮箱。

用途：

- 作为统一事件入口
- 开启 Gmail `watch`
- 提供邮件内容给分类器判断

### 2. Google Cloud 项目

需要一个自己的 Google Cloud 项目，并启用：

- `Gmail API`
- `Cloud Pub/Sub API`

用途：

- 建立 Gmail mailbox change event 到 Pub/Sub 的链路
- 提供 OAuth 客户端

### 3. QQ Bot 可用目标

需要 OpenClaw QQ Bot 已可用，并且你已经拿到一个可投递目标，例如：

- `qqbot:c2c:<OPENID>`
- `qqbot:group:<GROUP_OPENID>`

注意：

- 这不是 QQ 号
- 这不是 QQ 邮箱
- 这是 OpenClaw QQ Bot 已知的投递地址

### 4. OpenClaw 运行环境

需要本机已有可工作的 OpenClaw。

用途：

- 作为邮件重要性判断层
- 作为摘要生成层
- 作为 QQ 通知发送层
- 作为偏好学习入口

## 必需软件

### 1. Python

要求：

- Python `>= 3.13`

用途：

- 运行 `mail-bridge` 服务
- 执行 Gmail OAuth bootstrap
- 执行测试和本地工具脚本

### 2. Node.js

要求：

- 用于运行 OpenClaw

用途：

- 运行 OpenClaw Gateway
- 运行 OpenClaw QQ Bot 插件

### 3. OpenClaw CLI

要求：

- 本机可执行 `openclaw`
- 或使用绝对路径指向 `openclaw.cmd`

用途：

- `mail-bridge` 调 OpenClaw 做分类
- QQ Bot 通知发送

### 4. Google Cloud SDK（推荐）

要求：

- `gcloud`

用途：

- 初始化 ADC（Application Default Credentials）
- 调试 Pub/Sub / 项目配置

## 本地文件与凭据

你至少需要准备这些本地文件：

### 1. OAuth client 文件

- `credentials.json`

来源：

- Google Cloud Console 创建 OAuth Desktop Client 后下载

### 2. Gmail OAuth token

- `.secrets/gmail-token.json`

来源：

- 运行 `python -m mail_bridge.bootstrap_oauth` 生成

### 3. Pub/Sub ADC 凭据

推荐方式：

- `gcloud auth application-default login`

如果你选择复制凭据文件，也应放在本地私有目录中，例如：

- `.secrets/gcloud-adc.json`

## 网络与运行条件

### 1. 不需要公网

这套项目当前验证通过的路径是：

- `Pub/Sub StreamingPull`

也就是说：

- 不需要公开 HTTP 回调地址
- 不需要自己暴露 webhook 到公网

### 2. 机器需要常驻在线

因为当前使用的是本地常驻消费模式：

- Gmail 事件进入 Pub/Sub
- 本地 `mail-bridge` 持续拉取事件

所以机器需要保持在线。

## 可选组件

### 1. NSSM（Windows 服务）

如果你希望常驻后台运行，推荐使用：

- `NSSM`

用途：

- 把 `mail-bridge` 做成 Windows 服务
- 把 `OpenClaw Gateway` 做成 Windows 服务

### 2. SQLite 查看工具

不是必须，但调试时会方便。

用途：

- 查看 `data/mail-bridge.db`
- 检查 processed messages / PubSub ledger

## 最小可运行组合

一个最小可用部署至少包括：

- Gmail 账号
- Google Cloud 项目
- Gmail API + Pub/Sub API
- `credentials.json`
- Gmail OAuth token
- ADC 凭据
- Python 环境
- OpenClaw 可运行
- QQ Bot 已拿到目标地址

## 不要提前承诺的能力

如果你要公开发布，文档里不要默认承诺这些能力：

- 普通用户零配置可用
- 不需要 Google Cloud
- 不需要 OpenClaw
- 不需要本地常驻服务
- 直接支持所有邮箱服务商

当前最准确的描述应该是：

- **这是一个 self-hosted、本地优先、Gmail 为入口的 AI 邮件提醒桥接系统**
