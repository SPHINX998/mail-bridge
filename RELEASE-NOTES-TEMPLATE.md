# First Release Template

下面这份可以直接当 GitHub 首次发布说明来改。

---

## `mail-bridge` public release

`mail-bridge` 是一个 self-hosted、local-first 的 Gmail 实时邮件提醒桥接系统。

核心路径很简单：

- Gmail `watch` + Pub/Sub 作为实时事件入口
- `mail-bridge` 拉取最小邮件上下文
- OpenClaw 判断这封邮件是否重要，并生成摘要
- 只有重要邮件才通过 OpenClaw QQ Bot 发送 QQ 提醒

这个仓库当前更适合：

- 想要真实邮件 -> AI 判断 -> QQ 提醒链路的人
- 能接受 self-hosted、本地部署、手动配置 OAuth / Pub/Sub 的用户
- 希望把“邮件重要性判断”交给 OpenClaw，而不是写一堆硬编码规则的人

当前公开版默认边界：

- 只处理 Gmail 主入口
- 只处理新邮件
- 只处理 `INBOX`
- 不做自动回复、自动归档、自动打标
- 通知依赖 OpenClaw QQ Bot

## Attribution

This public release-ready repository package was assembled by OpenAI Codex.

Local runtime configuration, credentials, deployment, and ongoing operation remain the responsibility of the repository maintainer.

## Before use

使用前请先看：

- `README.md`
- `docs/QUICKSTART.md`
- `docs/DEPLOYMENT.md`
- `docs/CONFIGURATION.md`
- `PUBLISHING-CHECKLIST.md`

如果你准备 fork 或二次发布，建议先运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepublish-check.ps1
```
