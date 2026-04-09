param(
    [switch]$InstallDeps
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendRoot = Join-Path $projectRoot "frontend"
$envFile = Join-Path $projectRoot ".env"
$envExampleFile = Join-Path $projectRoot ".env.example"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Ensure-Command {
    param(
        [string]$Name,
        [string]$InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name 未安装或不可用。$InstallHint"
    }
}

Write-Step "检查基础环境"
Ensure-Command -Name "python" -InstallHint "请先安装 Python 3.10 及以上版本。"
Ensure-Command -Name "npm" -InstallHint "请先安装 Node.js 18 及以上版本。"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExampleFile) {
        Copy-Item $envExampleFile $envFile
        Write-Warning "已根据 .env.example 创建 .env，请先填入真实密钥后重新运行。"
    } else {
        Write-Warning "未找到 .env 文件，请先创建后再运行。"
    }
    exit 1
}

if ($InstallDeps) {
    Write-Step "安装 Python 依赖"
    & python -m pip install -r (Join-Path $projectRoot "requirements.txt")

    Write-Step "安装前端依赖"
    Push-Location $frontendRoot
    try {
        & npm install
    } finally {
        Pop-Location
    }
}

Write-Step "启动后端服务"
$backendCommand = "Set-Location '$projectRoot'; python api_server.py"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $backendCommand
) | Out-Null

Write-Step "启动前端服务"
$frontendCommand = "Set-Location '$frontendRoot'; npm.cmd run dev"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $frontendCommand
) | Out-Null

Write-Step "启动完成"
Write-Host "后端默认地址: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "前端默认地址: http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "如果是首次运行，建议使用: .\start_dev.ps1 -InstallDeps" -ForegroundColor Yellow
