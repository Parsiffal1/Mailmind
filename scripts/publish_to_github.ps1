param(
    [string]$RemoteUrl = "https://github.com/Parsiffal1/Mailmind.git",
    [string]$Branch = "main",
    [string]$Message = "chore: publish MailMind repo"
)

$ErrorActionPreference = "Stop"

function Fail($Message) {
    Write-Error $Message
    exit 1
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail "Git is not installed or not available in PATH. Install Git for Windows, reopen the terminal, then run this script again."
}

$forbidden = @(
    ".env",
    "credentials.json",
    "token.json",
    "data",
    "attachments",
    "chroma",
    "dashboard/node_modules",
    "dashboard/.next",
    "dashboard/out",
    "dashboard/dist",
    "release"
)

foreach ($path in $forbidden) {
    if (Test-Path $path) {
        Write-Host "Local-only path exists and should remain ignored: $path"
    }
}

$secretPatterns = @(
    "ANTHROPIC_API_KEY\s*=\s*.+",
    "VOYAGE_API_KEY\s*=\s*.+",
    "TELEGRAM_BOT_TOKEN\s*=\s*.+",
    "sk-ant-",
    "xoxb-",
    "AIza",
    "private_key",
    '"refresh_token"\s*:'
)

$scanFiles = Get-ChildItem -Recurse -File |
    Where-Object {
        $_.FullName -notmatch "\\node_modules\\|\\.next\\|\\out\\|\\dist\\|\\__pycache__\\|\\.pytest_cache\\|\\data\\|\\attachments\\|\\chroma\\|\\release\\" -and
        $_.Name -notin @(".env", "credentials.json", "token.json")
    }

foreach ($pattern in $secretPatterns) {
    $hits = $scanFiles | Select-String -Pattern $pattern -CaseSensitive:$false
    if ($hits) {
        $hits | Select-Object Path, LineNumber, Line
        Fail "Potential secret pattern found: $pattern"
    }
}

if (-not (Test-Path ".git")) {
    git init
}

git branch -M $Branch

$existingRemote = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin $RemoteUrl
} elseif ($existingRemote -ne $RemoteUrl) {
    git remote set-url origin $RemoteUrl
}

git add `
    .gitignore `
    .env.example `
    LICENSE `
    README.md `
    README.zh.md `
    README.zh-CN.md `
    SECURITY.md `
    pytest.ini `
    requirements.txt `
    .github `
    mailmind `
    dashboard/app `
    dashboard/public `
    dashboard/package.json `
    dashboard/package-lock.json `
    dashboard/next.config.js `
    docs `
    eval `
    prompts `
    scripts `
    tests

git status --short
git commit -m $Message
git push -u origin $Branch

Write-Host "Published MailMind to $RemoteUrl on branch $Branch"
