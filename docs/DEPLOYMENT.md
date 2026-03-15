# 部署文档

这份文档描述的是当前最稳的部署方式：

- `Gmail watch`
- `Pub/Sub StreamingPull`
- `mail-bridge` 本地常驻
- `OpenClaw` 负责判断与通知
- `QQ Bot` 负责把重要提醒发到 QQ

这不是 SaaS 部署文档，而是 **self-hosted 本地部署文档**。

## 1. 克隆项目

```powershell
git clone <your-repo-url>
cd mail-bridge
```

## 2. 创建 Python 虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## 3. 创建 Google Cloud 资源

在 Google Cloud Console 中准备：

- 一个项目
- 启用 `Gmail API`
- 启用 `Cloud Pub/Sub API`
- 创建 Gmail OAuth Desktop Client
- 创建 Pub/Sub Topic
- 创建 Pub/Sub Subscription

推荐最小结构：

- Topic：接 Gmail watch 事件
- Subscription：给本机 `mail-bridge` 消费

## 4. 下载 OAuth client 文件

把 Google Cloud Console 下载的 Desktop Client JSON 放到项目根目录：

- `credentials.json`

## 5. 获取 Gmail OAuth token

```powershell
.\.venv\Scripts\Activate.ps1
python -m mail_bridge.bootstrap_oauth
```

成功后会在本地生成 Gmail token 文件，例如：

- `.secrets/gmail-token.json`

## 6. 配置 Pub/Sub 本地凭据

推荐使用：

```powershell
gcloud auth application-default login
```

如果你的实现要求显式文件路径，可以把 ADC 凭据放到本地私有目录，例如：

- `.secrets/gcloud-adc.json`

## 7. 配置 `.env`

复制模板：

```powershell
Copy-Item .\.env.example .\.env
```

然后按你的环境填写。

最关键的字段是：

- `APP_HOST`
- `APP_PORT`
- `GMAIL_USER_EMAIL`
- `GMAIL_WATCH_TOPIC_NAME`
- `PUBSUB_SUBSCRIPTION_NAME`
- `GMAIL_OAUTH_CLIENT_FILE`
- `GMAIL_OAUTH_TOKEN_FILE`
- `GCP_SERVICE_ACCOUNT_FILE`
- `OPENCLAW_COMMAND`
- `OPENCLAW_AGENT_ID`
- `OPENCLAW_SESSION_ID`
- `OPENCLAW_JSON_MODEL`
- `NOTIFIER_MODE`
- `QQ_TARGET`
- `MEMENTO_RULES_FILE`

## 8. 验证 OpenClaw 可用

确保下面命令能工作：

```powershell
openclaw gateway status
openclaw skills list
```

如果你用的是 Windows 服务方式，请尽量把：

- `OPENCLAW_COMMAND`

写成绝对路径，例如：

- `C:/Users/<your-user>/AppData/Roaming/npm/openclaw.cmd`

## 9. 本地前台启动 `mail-bridge`

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn mail_bridge.main:app --host 127.0.0.1 --port 8787
```

## 10. 健康检查

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8787/healthz'
Invoke-RestMethod -Uri 'http://127.0.0.1:8787/watch/status'
Invoke-RestMethod -Uri 'http://127.0.0.1:8787/preferences'
```

## 11. 发送一次端到端测试

推荐两种方式：

### 方法 A：给自己的 Gmail 发测试邮件

从别的邮箱发一封邮件到目标 Gmail。

建议主题包含明显标记，例如：

- `MAIL_BRIDGE_TEST`

### 方法 B：使用项目自带脚本发测试邮件

前提：你的 Gmail OAuth scope 允许该脚本发送。

```powershell
python -m mail_bridge.send_test_message --subject "MAIL_BRIDGE_TEST" --body "This is a test"
```

## 12. 看日志确认链路

重点看：

- `data/mail-bridge-service.log`
- `data/mail-bridge-service.err.log`

健康链路通常会出现：

- `pubsub_history_event_received`
- `history_batch_loaded`
- `message_classified`
- `notification_sent`

## 13. 可选：做成 Windows 服务

如果你希望后台常驻，推荐：

- 用 NSSM 把 `mail-bridge` 做成服务
- 用 NSSM 把 OpenClaw Gateway 做成服务

原则：

- 只保留一套服务实例
- 不要同时跑“手工前台进程 + Windows 服务”两套同类进程

## 当前推荐部署模式

对公开仓库使用者，建议优先按这个顺序：

1. 先前台跑通
2. 再验证 QQ 通知
3. 再验证偏好纠正写回
4. 最后再做后台服务化

不要一上来就先做服务注册，否则排障会更麻烦。

## 已知边界

这套部署当前默认假设：

- Gmail 是唯一主事件源
- 只处理新邮件
- 只处理 `INBOX`
- 只截取正文前几 KB
- OpenClaw 负责重要性判断和摘要生成
- 只有重要邮件才会发 QQ 通知

## 故障排查起点

如果部署失败，优先排查这四类问题：

### 1. Gmail OAuth 问题

看：

- token 文件是否生成
- OAuth scope 是否正确

### 2. Pub/Sub 问题

看：

- topic / subscription 名称是否正确
- Gmail push 账号是否有 topic publisher 权限
- ADC 是否有效

### 3. OpenClaw 问题

看：

- `openclaw gateway status`
- `openclaw skills list`
- `OPENCLAW_COMMAND` 是否为绝对路径

### 4. QQ 通知问题

看：

- `QQ_TARGET` 是否是可投递目标
- OpenClaw QQ Bot 插件是否可用
- 该目标是否已经被 bot 识别
