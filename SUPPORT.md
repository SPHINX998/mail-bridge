# Support

## Before opening an issue

先按这个顺序自查：

1. 看 `README.md`
2. 看 `docs/QUICKSTART.md`
3. 看 `docs/CONFIGURATION.md`
4. 看 `docs/runbooks/OPERATIONS.md`
5. 跑一次 `scripts/prepublish-check.ps1`

## Best-effort support scope

这个仓库更适合处理下面几类问题：

- Gmail `watch` / Pub/Sub 配置错误
- OpenClaw 调用链路问题
- QQ Bot 投递问题
- 本地服务运行和日志观察问题
- 公开仓库文档或示例配置问题

## What to include in a good support request

请尽量附带：

- 你使用的操作系统
- Python 版本
- 你使用的 OpenClaw 运行方式
- 关键日志片段（先脱敏）
- 你已经尝试过哪些排查动作
- 预期行为和实际行为

## What not to include

不要贴这些内容：

- `.env` 全文
- `credentials.json`
- `.secrets/` 内容
- 真实 OAuth token
- 真实 QQ 目标
- 任何可直接复用的私钥或 access token
