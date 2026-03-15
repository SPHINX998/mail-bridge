[CmdletBinding()]
param(
    [string]$Root = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Root)) {
    $scriptPath = if ($PSCommandPath) { $PSCommandPath } else { $MyInvocation.MyCommand.Path }
    $scriptDir = Split-Path -Parent $scriptPath
    $Root = (Resolve-Path (Join-Path $scriptDir "..")).Path
} else {
    $Root = (Resolve-Path $Root).Path
}

Write-Host "==> prepublish check root: $Root"

$script:failed = $false

function Add-Finding {
    param(
        [string]$Message
    )

    $script:failed = $true
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Add-Pass {
    param(
        [string]$Message
    )

    Write-Host "[PASS] $Message" -ForegroundColor Green
}

$forbiddenPaths = @(
    ".env",
    "credentials.json",
    ".secrets",
    ".venv",
    ".pytest_cache",
    "data",
    "mail_bridge.egg-info"
)

foreach ($relativePath in $forbiddenPaths) {
    $target = Join-Path $Root $relativePath
    if (Test-Path $target) {
        Add-Finding "Forbidden path exists: $relativePath"
    } else {
        Add-Pass "Forbidden path absent: $relativePath"
    }
}

$runtimeDirs = Get-ChildItem -Path $Root -Recurse -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "__pycache__" }

if ($runtimeDirs) {
    foreach ($dir in $runtimeDirs) {
        $relative = $dir.FullName.Substring($Root.Length).TrimStart("\", "/")
        Add-Finding "Runtime cache directory exists: $relative"
    }
} else {
    Add-Pass "No __pycache__ directories found"
}

$sensitivePatterns = @(
    @{ Name = "Authorization Bearer"; Regex = "Authorization:\s*Bearer\s+" },
    @{ Name = "Google access token"; Regex = "ya29\.[0-9A-Za-z\-_]+" },
    @{ Name = "GitHub token"; Regex = "ghp_[0-9A-Za-z]+" },
    @{ Name = "Slack bot token"; Regex = "xoxb-[0-9A-Za-z\-]+" },
    @{ Name = "QQ direct target"; Regex = "qqbot:c2c:(?!YOUR_OPENID\b|OPENID\b)[A-Za-z0-9_-]+" },
    @{ Name = "QQ group target"; Regex = "qqbot:group:(?!YOUR_GROUP_OPENID\b|GROUP_OPENID\b)[A-Za-z0-9_-]+" },
    @{ Name = "BEGIN PRIVATE KEY"; Regex = "BEGIN PRIVATE KEY" }
)

$textExtensions = @(".md", ".py", ".mjs", ".toml", ".json", ".yml", ".yaml", ".ps1", ".txt", ".example")
$textFiles = Get-ChildItem -Path $Root -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object {
        (($textExtensions -contains $_.Extension.ToLowerInvariant()) -or $_.Name -eq ".env.example") -and
        $_.FullName -ne $scriptPath
    }

foreach ($pattern in $sensitivePatterns) {
    $matches = $textFiles | Select-String -Pattern $pattern.Regex
    foreach ($match in $matches) {
        $relative = $match.Path.Substring($Root.Length).TrimStart("\", "/")
        Add-Finding ("Sensitive pattern [{0}] -> {1}:{2}" -f $pattern.Name, $relative, $match.LineNumber)
    }
}

if (-not $script:failed) {
    Add-Pass "No forbidden files, runtime artifacts, or sensitive patterns found"
    exit 0
}

Write-Host ""
Write-Host "prepublish check failed" -ForegroundColor Yellow
exit 1
