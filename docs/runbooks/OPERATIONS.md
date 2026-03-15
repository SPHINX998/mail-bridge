# Operations

## 推荐运维原则

- 先前台跑通，再服务化
- `mail-bridge` 和 OpenClaw Gateway 都只保留一套实例
- 不要同时保留“手工前台进程 + Windows 服务”两套同类实例
- 所有真实密钥只放本地，不放 Git

## `mail-bridge` 常用命令

### 查询服务状态

```powershell
sc query mail-bridge
```

### 启动服务

```powershell
sc start mail-bridge
```

### 停止服务

```powershell
sc stop mail-bridge
```

### 重启服务

```powershell
sc stop mail-bridge
sc start mail-bridge
```

## OpenClaw Gateway 常用命令

如果你把 OpenClaw Gateway 也做成了 Windows 服务，请用你自己的服务名。常见做法例如：

```powershell
sc query OpenClawService
sc start OpenClawService
sc stop OpenClawService
```

如果你是前台调试：

```powershell
openclaw gateway status
openclaw skills list
```

## 健康检查

### App health

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8787/healthz'
```

### Watch status

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8787/watch/status'
```

### Read current preference notes

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8787/preferences'
```

## 偏好写入

### Append a preference note

```powershell
python -m mail_bridge.add_preference_note --note "带明确截止时间的审批邮件必须提醒"
```

### Append a structured preference rule

```powershell
python -m mail_bridge.add_preference_rule --scope sender --value "王总" --action always_notify --reason "老板邮件通常需要立即处理"
```

## 日志

### `mail-bridge` 日志

- `data/mail-bridge-service.log`
- `data/mail-bridge-service.err.log`

### 健康事件通常会看到

- `pubsub_history_event_received`
- `history_batch_loaded`
- `message_classified`
- `message_recorded`
- `notification_sent`

## 状态检查

### Read recent processed messages

```powershell
cd D:\path\to\mail-bridge
.\.venv\Scripts\python -c "import sqlite3, json; conn=sqlite3.connect('data/mail-bridge.db'); conn.row_factory=sqlite3.Row; rows=conn.execute('select subject, notified, created_at, classification_json from processed_messages order by created_at desc limit 10').fetchall(); print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))"
```

### Read recent Pub/Sub events

```powershell
cd D:\path\to\mail-bridge
.\.venv\Scripts\python -c "import sqlite3, json; conn=sqlite3.connect('data/mail-bridge.db'); conn.row_factory=sqlite3.Row; rows=conn.execute('select pubsub_message_id, history_id, received_at from pubsub_events order by received_at desc limit 10').fetchall(); print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))"
```

## 常见问题

### `watch/status` shows `configured=false`

常见原因：

- Gmail OAuth token 缺失
- Gmail `watch` 续订失败
- 服务早于 OAuth 初始化启动

### Pub/Sub events not arriving

检查：

- topic name
- subscription name
- ADC credentials
- Gmail topic publish permission

### Notifications not sent

检查：

- `message_classified` 日志
- `OPENCLAW_COMMAND`
- `OPENCLAW_AGENT_ID`
- `OPENCLAW_JSON_MODEL`
- `OPENCLAW_JSON_THINKING_LEVEL`
- `QQ_TARGET`
- `openclaw gateway status`

### OpenClaw service / gateway confusion

如果你明明看到端口有监听，但 `openclaw gateway status` 的服务字段显示异常，不要只盯着那一项。

应该同时检查：

- OpenClaw gateway 是否真的在监听目标端口
- `mail-bridge` 是否能正常调用 `openclaw`
- QQ Bot 插件是否真的可投递

## 服务化建议

如果你最终做 Windows 服务，建议：

- `mail-bridge` 用 NSSM 托管
- OpenClaw Gateway 用 NSSM 托管
- `OPENCLAW_COMMAND` 使用绝对路径
- 对外只保留一份服务实例
- 更新前先记录当前参数
