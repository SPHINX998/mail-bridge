# GitHub 发布检查清单

把这个项目公开之前，先过完这份清单。

## 一、绝对不要提交的内容

确认下面这些内容**没有**进入 Git：

- `.env`
- `.secrets/`
- `credentials.json`
- Gmail OAuth token
- ADC 凭据
- 任何 Google Client Secret
- 任何 OpenClaw token / gateway token
- 任何 QQ Bot 凭据
- 真实 `QQ_TARGET`
- 本机路径里包含隐私信息的导出文件

## 二、要保留的公开模板

确认下面这些文件存在并可公开：

- `.env.example`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/CONFIGURATION.md`
- `docs/runbooks/OPERATIONS.md`
- `docs/QUICKSTART.md`
- `docs/DEPLOYMENT.md`
- `docs/USAGE.md`
- `docs/REQUIREMENTS.md`

## 三、README 里要明确写的事

公开仓库首页至少要明确：

- 这是 self-hosted 项目
- Gmail 是主事件入口
- OpenClaw 负责重要性判断和通知编排
- QQ 通知依赖 OpenClaw QQ Bot
- 当前更适合 power-user，而不是普通零配置用户
- 当前默认路径是本地部署

## 四、发布前手动检查

### 0. 先跑自动检查

先在仓库根目录运行：

```powershell
pwsh -File .\scripts\prepublish-check.ps1
```

或者：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepublish-check.ps1
```

这个脚本会优先检查：

- 常见敏感文件是否存在
- 常见运行产物是否残留
- 常见敏感关键词是否还在文本文件里
- 文档里是否仍有明显的私有配置痕迹

### 1. 查敏感字段

至少在仓库里搜这些关键词：

- `client_secret`
- `apiKey`
- `token`
- `gmail-token`
- `gcloud-adc`
- `qqbot:c2c:`
- `Authorization`

### 2. 查本机私有路径

检查文档里是否还残留这些不能公开的东西：

- 真实邮箱地址（如果你不想公开）
- 真实 QQ 标识
- 真实 Windows 用户目录
- 本机私有调试记录

### 3. 查运行产物

不要提交：

- `data/*.db`
- 日志文件
- `.pytest_cache`
- `.venv`
- 本地 transcript 导出

## 五、推荐的发布顺序

1. 先整理公开文档
2. 跑 `scripts/prepublish-check.ps1`
3. 再检查 `.gitignore`
4. 再手动全文搜敏感信息
5. 再新建公开仓库
6. 最后推送

## 六、最重要的原则

这个项目完全值得公开，但公开时要保证两件事：

- **真实**：不要夸大成零配置产品
- **安全**：不要把任何真实凭据带进仓库
