# Security Policy

## Supported scope

这个仓库当前更偏向 self-hosted、本地部署和 power-user 使用场景。

如果你发现的是下面这类问题，欢迎报告：

- 凭据泄漏风险
- OAuth token / ADC / secret 文件处理问题
- 本地 API 暴露不当
- 日志中可能泄露敏感数据
- 命令执行链路存在明显安全边界问题

## Do not open public issues for secrets

如果问题包含以下任一内容，不要直接发公开 issue：

- 真实 token
- 真实 client secret
- 真实 QQ Bot 凭据
- 真实邮箱地址和会话导出
- 可复用的私有配置文件

请先自行做最小化脱敏，再描述问题。

## How to report

当前推荐的最安全做法：

1. 先不要公开贴凭据
2. 最小化复现问题
3. 把环境、影响范围、复现步骤写清楚
4. 如果 issue 可能导致直接凭据泄漏，先不要公开发全文

## Security expectations

这个项目默认假设：

- 凭据只保存在本地
- `.env`、`.secrets/`、`credentials.json` 不进入 Git
- 发布前运行 `scripts/prepublish-check.ps1`

## Hard boundary

这个仓库不是托管 SaaS。

它不提供集中式密钥托管、安全审计平台或统一云侧隔离保证。部署者需要自行对本机、账号权限和凭据管理负责。
