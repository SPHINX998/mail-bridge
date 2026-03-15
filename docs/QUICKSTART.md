# 10 分钟快速上手

这份文档给的是最短路径。

前提：你已经愿意接受这是一个 self-hosted、本地部署项目。

## 你至少需要这些东西

- 一个 Gmail 账号
- 一个 Google Cloud 项目
- 已启用 `Gmail API` 和 `Cloud Pub/Sub API`
- 一个 OAuth Desktop Client 的 `credentials.json`
- 本机 Python `>= 3.13`
- 本机已能运行 OpenClaw
- 一个可投递的 QQ Bot 目标

详细清单见：

- `REQUIREMENTS.md`

## 第 1 步：安装依赖

```powershell
git clone <your-repo-url>
cd mail-bridge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## 第 2 步：准备配置

复制示例配置：

```powershell
Copy-Item .\.env.example .\.env
```

至少填好这些值：

- `GMAIL_USER_EMAIL`
- `GMAIL_WATCH_TOPIC_NAME`
- `PUBSUB_SUBSCRIPTION_NAME`
- `OPENCLAW_COMMAND`
- `OPENCLAW_AGENT_ID`
- `OPENCLAW_SESSION_ID`
- `QQ_TARGET`
- `MEMENTO_RULES_FILE`

## 第 3 步：做 Gmail OAuth

把 `credentials.json` 放到项目根目录后执行：

```powershell
python -m mail_bridge.bootstrap_oauth
```

## 第 4 步：准备 ADC

推荐：

```powershell
gcloud auth application-default login
```

## 第 5 步：启动 OpenClaw

确认下面命令正常：

```powershell
openclaw gateway status
openclaw skills list
```

## 第 6 步：启动 mail-bridge

```powershell
uvicorn mail_bridge.main:app --host 127.0.0.1 --port 8787
```

## 第 7 步：做健康检查

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8787/healthz'
Invoke-RestMethod -Uri 'http://127.0.0.1:8787/watch/status'
```

## 第 8 步：发一封测试邮件

给目标 Gmail 发一封主题明显的测试邮件，例如：

- `MAIL_BRIDGE_TEST`

如果链路正常：

- `mail-bridge` 会收到 Gmail 事件
- OpenClaw 会判断重要性
- 如果判定重要，就会通过 QQ Bot 发提醒

## 第 9 步：纠正一次偏好

在 OpenClaw 对话里说：

- `以后招聘平台营销邮件不要提醒我。`
- `以后王总发来的邮件必须提醒我。`

如果配置正确，OpenClaw 会把偏好写回 `mail-bridge`。

## 第 10 步：决定是否做成后台服务

建议先前台跑通，再决定是否：

- 用 NSSM 把 `mail-bridge` 做成服务
- 用 NSSM 把 OpenClaw Gateway 做成服务

## 如果你卡住了

优先看：

- `docs/DEPLOYMENT.md`
- `docs/USAGE.md`
- `docs/runbooks/OPERATIONS.md`
