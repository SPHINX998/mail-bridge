# Contributing

感谢你准备改进这个项目。

这个仓库不是通用邮件客户端，也不是零配置产品。提交前请先理解它当前的边界：

- Gmail 是主事件入口
- OpenClaw 负责重要性判断与摘要
- QQ 通知通过 OpenClaw QQ Bot 投递
- 当前默认运行模式是本地 `StreamingPull`

## 开发环境

推荐环境：

- Python `3.13+`
- Windows PowerShell
- 本地可用的 OpenClaw CLI
- Gmail OAuth / Pub/Sub 配置

创建虚拟环境并安装：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .[dev]
```

## 提交原则

- 优先修根因，不做表层补丁
- 保持事件流可观测
- 不要把项目改造成“大而全”邮件平台
- 配置键、运行流程、运维方式有变化时，同步更新文档
- 不要提交真实凭据、真实邮箱、真实 QQ 目标

## 本地验证

至少做这两步：

```powershell
python -m pytest
pwsh -File .\scripts\prepublish-check.ps1
```

如果你的环境没有 `pwsh`，可改用：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepublish-check.ps1
```

## Pull Request 建议

PR 描述最好包含：

- 改了什么
- 为什么改
- 影响了哪些配置或运行路径
- 如何验证

如果改动涉及 Gmail、Pub/Sub、OpenClaw 或 QQ 投递链路，请明确写出：

- 是否影响现有本地部署
- 是否需要新增配置项
- 是否需要用户重新授权或重启服务

## GitHub 协作约定

仓库已经补齐了这些基础协作文件：

- Issue templates
- Pull request template
- CI workflow
- `SECURITY.md`
- `SUPPORT.md`

如果你要提交公开协作相关改动，尽量与这些文件保持一致。
