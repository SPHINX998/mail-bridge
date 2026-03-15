# Configuration

## 配置来源

项目运行时主要依赖：

- `.env`

本地敏感文件通常包括：

- `.secrets/gmail-token.json`
- `.secrets/gcloud-adc.json`
- `credentials.json`

这些文件都不应该提交到 Git。

## 核心文件

### `credentials.json`

Google OAuth Desktop Client JSON。

来源：

- Google Cloud Console 下载

推荐放置位置：

- 项目根目录 `credentials.json`

### Gmail OAuth token

通过下面命令生成：

```powershell
python -m mail_bridge.bootstrap_oauth
```

推荐路径：

- `.secrets/gmail-token.json`

### ADC credentials

推荐方式：

```powershell
gcloud auth application-default login
```

如果使用文件路径方式，推荐放到：

- `.secrets/gcloud-adc.json`

## 主要 `.env` 键

### App

- `APP_HOST`
- `APP_PORT`

### Gmail

- `GMAIL_USER_EMAIL`
- `GMAIL_WATCH_TOPIC_NAME`
- `GMAIL_OAUTH_SCOPES`
- `GMAIL_WATCH_LABEL_IDS`
- `GMAIL_WATCH_LABEL_FILTER_BEHAVIOR`
- `GMAIL_OAUTH_CLIENT_FILE`
- `GMAIL_OAUTH_TOKEN_FILE`
- `GMAIL_WATCH_CHECK_INTERVAL_MINUTES`
- `GMAIL_WATCH_RENEW_MARGIN_HOURS`

### Pub/Sub

- `PUBSUB_MODE`
- `PUBSUB_SUBSCRIPTION_NAME`
- `PUBSUB_EXPECTED_AUDIENCE`
- `PUBSUB_EXPECTED_SERVICE_ACCOUNT_EMAIL`
- `GCP_SERVICE_ACCOUNT_FILE`

### Processing

- `STATE_DB_PATH`
- `BODY_PREVIEW_BYTES`
- `MAX_ATTACHMENT_NAMES`
- `OPENCLAW_COMMAND`
- `OPENCLAW_AGENT_ID`
- `OPENCLAW_SESSION_ID`
- `OPENCLAW_JSON_PROVIDER`
- `OPENCLAW_JSON_MODEL`
- `OPENCLAW_JSON_THINKING_LEVEL`
- `OPENCLAW_TIMEOUT_SECONDS`

### Rules

- `IMPORTANCE_POLICY_NOTE`
- `MEMENTO_RULES_FILE`

### Notification

- `NOTIFIER_MODE`
- `QQ_TARGET`

## OpenClaw 推荐配置

### `OPENCLAW_COMMAND`

推荐写绝对路径，例如：

- `C:/Users/<your-user>/AppData/Roaming/npm/openclaw.cmd`

原因：

- Windows 服务环境下不要依赖 `PATH`
- 这样更利于 `mail-bridge` 推断到正确的 OpenClaw 用户目录

### `OPENCLAW_AGENT_ID`

推荐值：

- `main`

除非你明确维护了一套专门用于邮件任务的 agent。

### `OPENCLAW_SESSION_ID`

推荐值：

- `mail-bridge-inbox-clean`

这样可以把邮件判断上下文稳定绑定在一个独立会话里。

### `OPENCLAW_JSON_MODEL`

推荐从一个稳定的文本模型开始，例如：

- `claude-sonnet-4-6`

### `OPENCLAW_JSON_THINKING_LEVEL`

推荐值：

- `off`

因为这里主要是结构化判断任务，不需要很高的推理展开。

## Gmail OAuth scope 建议

### `GMAIL_OAUTH_SCOPES`

推荐值：

- 只读运行：`https://www.googleapis.com/auth/gmail.readonly`
- 如果要用自带脚本发送测试邮件：`https://www.googleapis.com/auth/gmail.modify`

如果你扩大 scope 后，要重新执行 OAuth bootstrap 让用户重新授权。

## 通知配置说明

### `QQ_TARGET`

这里填的不是 QQ 号，而是 OpenClaw QQ Bot 可直接投递的目标，例如：

- `qqbot:c2c:OPENID`
- `qqbot:group:GROUP_OPENID`

## 本地偏好反馈接口

项目会暴露本地接口：

- `GET /preferences`
- `POST /preferences/notes`
- `POST /preferences/rules`

示例：

```json
{
  "scope": "sender",
  "value": "王总",
  "action": "always_notify",
  "reason": "老板邮件通常需要立即处理"
}
```

支持的 `scope`：

- `sender`
- `domain`
- `keyword`
- `topic`
- `pattern`

支持的 `action`：

- `always_notify`
- `never_notify`
- `brief`
- `summary`
- `full_excerpt`

## 修改配置后的建议动作

- 改 `.env` 后重启 `mail-bridge`
- 改 OpenClaw skill / session 注入逻辑后，必要时重建对应 session snapshot
- 改 Gmail OAuth scope 后重新授权

## 安全规则

- 可以提交 `.env.example`
- 不要提交 `.env`
- 不要提交 `credentials.json`
- 不要提交 `.secrets/`
- 不要在文档或日志里公开真实 token / client secret / QQ 目标
