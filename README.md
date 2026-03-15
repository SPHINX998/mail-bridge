# mail-bridge

A self-hosted Gmail -> OpenClaw -> QQ mail importance bridge.

`mail-bridge` 是一个**本地优先、实时、低打扰**的邮件提醒桥接系统。

它的目标不是做一个完整邮件客户端，而是：

- 实时接收 Gmail 新邮件事件
- 只提取判断所需的最小上下文
- 交给 OpenClaw 判断这封邮件对你是否重要
- 只有在重要时才通过 QQ Bot 给你发提醒
- 允许你通过和 OpenClaw 的自然对话，逐步纠正“以后这类邮件怎么处理”

## 适合谁

这个项目更适合：

- 想要 **Gmail -> AI -> QQ** 实时提醒链路的人
- 接受 self-hosted、本地部署的人
- 想把 OpenClaw 接进真实邮件流的人
- 更关心稳定和可控，而不是零配置体验的人

## 不适合谁

这个项目目前不适合：

- 追求零配置、开箱即用的普通用户
- 不想接触 Google Cloud / OAuth / Pub/Sub 的用户
- 需要 SaaS 托管产品体验的用户

## 核心特点

- **实时**：基于 Gmail `watch` + Pub/Sub
- **不轮询**：不是定时扫邮箱
- **低打扰**：只有重要邮件才提醒
- **本地优先**：当前验证路径不要求公网回调
- **AI 判断**：OpenClaw 负责重要性判断和摘要生成
- **可学习**：你可以直接纠正未来提醒偏好
- **可观测**：本地有状态库、日志、清晰的链路分层

## 当前推荐架构

```text
Gmail new mail
  -> Gmail watch
  -> Pub/Sub
  -> mail-bridge
  -> OpenClaw classify + summarize
  -> OpenClaw QQ Bot notify
```

## 快速开始

1. 准备 Gmail + Google Cloud + OpenClaw + QQ Bot
2. 复制 `.env.example` 到 `.env`
3. 运行 Gmail OAuth bootstrap
4. 启动 `mail-bridge`
5. 发一封测试邮件验证整条链路

详细步骤见：

- `docs/QUICKSTART.md`
- `docs/DEPLOYMENT.md`
- `docs/REQUIREMENTS.md`
- `docs/USAGE.md`

## 文档索引

- 架构：`docs/ARCHITECTURE.md`
- 配置：`docs/CONFIGURATION.md`
- 运维：`docs/runbooks/OPERATIONS.md`
- 快速上手：`docs/QUICKSTART.md`
- 部署：`docs/DEPLOYMENT.md`
- 使用：`docs/USAGE.md`
- 前置条件：`docs/REQUIREMENTS.md`

## 当前边界

第一版当前默认：

- 只处理 Gmail 主入口
- 只处理新邮件
- 只处理 `INBOX`
- 只做提醒，不做自动回复
- 不自动归档 / 打标 / 回复邮件
- QQ 通知依赖 OpenClaw QQ Bot

## 项目定位

这个仓库当前的准确定位是：

- **self-hosted 工具**
- **power-user 友好**
- **本地优先**
- **Gmail 单入口架构**

不是：

- 零配置产品
- 多租户 SaaS
- 通用邮件客户端

## 安全提醒

公开仓库前请务必确保没有提交这些内容：

- `.env`
- `.secrets/`
- `credentials.json`
- Gmail OAuth token
- ADC 凭据
- 真实 QQ 目标
- 任何 OpenClaw / QQ / Google 密钥

可参考：

- `PUBLISHING-CHECKLIST.md`
- `scripts/prepublish-check.ps1`

## 发布准备

如果你准备把这个目录直接推到 GitHub，建议在推送前至少做这三件事：

1. 运行 `scripts/prepublish-check.ps1`
2. 再手动检查 `.env.example`、`README.md`、`docs/`
3. 确认本地运行态目录没有被一起带进去

推荐命令：

```powershell
pwsh -File .\scripts\prepublish-check.ps1
```

如果你的环境没有 `pwsh`，也可以直接用 Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepublish-check.ps1
```

## 贡献

如果你准备继续演进这个公开版，可先看：

- `CONTRIBUTING.md`
- `REPO-METADATA.md`
- `AUTHORS.md`

## 构建归属说明

这份可公开发布的仓库版本（`mail-bridge-public`）由 OpenAI Codex 完整整理与构建发布物料，包括：

- 公开副本目录拆分
- 敏感信息剥离
- 文档体系补齐
- 示例配置整理
- 发布检查清单
- 发布前自检脚本

原本地运行工程、真实账号配置、服务部署与长期运营归仓库维护者负责。

## License

本仓库当前附带 `MIT` 许可证，方便个人学习、修改和二次发布。
