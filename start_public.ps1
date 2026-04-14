param(
    [string]$NgrokExePath = "C:\Users\Lenovo\Desktop\ngrok\ngrok.exe",
    [string]$NgrokDomain = "",
    [int]$BackendPort = 8000,
    [string]$OutputDir = "public_runtime",
    [string]$SubmissionDir = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputDirAbs = Join-Path $projectRoot $OutputDir
$traceFile = Join-Path $outputDirAbs "start_public.trace.log"
$runUrlFile = Join-Path $outputDirAbs "runtime_url.txt"
$qrImageFile = Join-Path $outputDirAbs "runtime_qr.png"
$qrNoteFile = Join-Path $outputDirAbs "runtime_qr_note.txt"
$backendOut = Join-Path $projectRoot "backend-dev.log"
$backendErr = Join-Path $projectRoot "backend-dev.err.log"
$ngrokOut = Join-Path $projectRoot "ngrok-frontend.log"
$ngrokErr = Join-Path $projectRoot "ngrok-frontend.err.log"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Trace {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    Add-Content -LiteralPath $traceFile -Value "$ts $Message"
}

function Resolve-SubmissionDir {
    param([string]$PreferredDir)
    if ($PreferredDir) {
        $p = Join-Path $projectRoot $PreferredDir
        if (Test-Path -LiteralPath $p) {
            return $p
        }
    }
    $candidate = Get-ChildItem -LiteralPath $projectRoot -Directory | Where-Object { $_.Name -like "1_*" } | Select-Object -First 1
    if ($candidate) {
        return $candidate.FullName
    }
    return $projectRoot
}

function Stop-PortProcess {
    param([int]$Port)
    $lines = netstat -ano | Select-String ":$Port"
    foreach ($line in $lines) {
        $parts = ($line.ToString().Trim() -split "\s+")
        if ($parts.Length -lt 5) { continue }
        if ($parts[0] -ne "TCP") { continue }
        $localAddr = $parts[1]
        $state = $parts[3]
        $procId = $parts[4]
        if ($localAddr -notmatch ":$Port$") { continue }
        if ($state -ne "LISTENING") { continue }
        if ($procId -match "^\d+$") {
            $targetPid = [int]$procId
            if ($targetPid -ne $PID) {
                Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Wait-Http {
    param([string]$Url, [int]$TimeoutSeconds = 40)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) { return $true }
        } catch {
            Start-Sleep -Milliseconds 700
        }
    }
    return $false
}

function Resolve-NgrokPath {
    param([string]$PreferredPath)
    if ($PreferredPath -and (Test-Path -LiteralPath $PreferredPath)) { return $PreferredPath }
    $cmd = Get-Command ngrok -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "Cannot find ngrok.exe. Install ngrok or pass -NgrokExePath."
}

function Wait-NgrokPublicUrl {
    param([int]$TimeoutSeconds = 25)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $ti = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels"
            $url = ($ti.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1).public_url
            if (-not $url) { $url = ($ti.tunnels | Select-Object -First 1).public_url }
            if ($url) { return $url }
        } catch {
            Start-Sleep -Milliseconds 700
        }
        Start-Sleep -Milliseconds 500
    }
    return $null
}

New-Item -ItemType Directory -Path $outputDirAbs -Force | Out-Null
Set-Content -LiteralPath $traceFile -Value "" -Encoding UTF8

$submissionDirAbs = Resolve-SubmissionDir -PreferredDir $SubmissionDir
New-Item -ItemType Directory -Path $submissionDirAbs -Force | Out-Null
$submissionUrlFallback = Join-Path $submissionDirAbs "run_url.txt"
$submissionQrFallback = Join-Path $submissionDirAbs "system_qr.png"

Write-Step "Prepare output directory"
Trace "prepare_output_dir"

Write-Step "Stop old backend/ngrok processes"
Trace "stop_old_processes_begin"
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force
Stop-PortProcess -Port $BackendPort
Trace "stop_old_processes_done"

foreach ($file in @($backendOut, $backendErr, $ngrokOut, $ngrokErr)) {
    if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file -Force }
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) { throw "Cannot find python in PATH." }

Write-Step "Start backend service"
Trace "backend_start_begin"
$backendProcess = Start-Process $pythonCmd.Source `
    -ArgumentList "api_server.py" `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -PassThru
Trace "backend_start_done pid=$($backendProcess.Id)"

if (-not (Wait-Http -Url "http://127.0.0.1:$BackendPort/api/health" -TimeoutSeconds 45)) {
    Trace "backend_health_failed"
    throw "Backend failed to start."
}
Trace "backend_health_ok"

$ngrokExe = Resolve-NgrokPath -PreferredPath $NgrokExePath

Write-Step "Start ngrok tunnel"
Trace "ngrok_start_begin"
$ngrokArgs = @("http", "$BackendPort")
if ($NgrokDomain) { $ngrokArgs += "--domain=$NgrokDomain" }

$ngrokProcess = Start-Process $ngrokExe `
    -ArgumentList $ngrokArgs `
    -RedirectStandardOutput $ngrokOut `
    -RedirectStandardError $ngrokErr `
    -PassThru
Trace "ngrok_start_done pid=$($ngrokProcess.Id)"

if (-not (Wait-Http -Url "http://127.0.0.1:4040/api/tunnels" -TimeoutSeconds 35)) {
    Trace "ngrok_local_api_failed"
    throw "ngrok local API is not available."
}
Trace "ngrok_local_api_ok"

$publicUrl = Wait-NgrokPublicUrl -TimeoutSeconds 25
if (-not $publicUrl) {
    Trace "public_url_missing"
    throw "Cannot resolve public URL from ngrok."
}
Trace "public_url_ok $publicUrl"

$nowText = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-Step "Write runtime URL file"
Trace "write_runtime_url_begin"
$runUrlText = @(
    "Current public URL (auto-updated by script)",
    "",
    "$publicUrl",
    "",
    "Generated at: $nowText",
    "Note: If ngrok warning page appears first, click Visit Site.",
    "Stability: URL remains unchanged only when -NgrokDomain is configured."
) -join "`r`n"
Set-Content -LiteralPath $runUrlFile -Value $runUrlText -Encoding UTF8
Trace "write_runtime_url_done"

Write-Step "Generate QR image"
Trace "qr_begin"
$qrDone = $false
try {
    $py = @"
import qrcode
url = r'''$publicUrl'''
out_file = r'''$qrImageFile'''
img = qrcode.make(url)
img.save(out_file)
"@
    $tmpPy = [System.IO.Path]::GetTempFileName() + ".py"
    Set-Content -LiteralPath $tmpPy -Value $py -Encoding UTF8
    & $pythonCmd.Source $tmpPy
    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $qrImageFile)) { $qrDone = $true }
    Remove-Item -LiteralPath $tmpPy -Force -ErrorAction SilentlyContinue
} catch {
    $qrDone = $false
}
Trace "qr_done status=$qrDone"

$qrStatus = if ($qrDone) { "success" } else { "failed (rerun script)" }
$qrNote = @(
    "Runtime QR note (auto-updated by script)",
    "",
    "URL: $publicUrl",
    "Generated at: $nowText",
    "QR file: runtime_qr.png",
    "QR generation: $qrStatus",
    "",
    "Stability: URL remains unchanged only when -NgrokDomain is configured."
) -join "`r`n"
Set-Content -LiteralPath $qrNoteFile -Value $qrNote -Encoding UTF8
Trace "write_qr_note_done"

Write-Step "Sync to submission folder"
Trace "sync_submission_begin"
# Update all existing non-readme txt files at submission root.
$submissionTxtFiles = Get-ChildItem -LiteralPath $submissionDirAbs -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -eq ".txt" -and $_.Name -ne "readme.txt" }
if ($submissionTxtFiles.Count -gt 0) {
    foreach ($f in $submissionTxtFiles) {
        Set-Content -LiteralPath $f.FullName -Value $publicUrl -Encoding UTF8
    }
} else {
    Set-Content -LiteralPath $submissionUrlFallback -Value $publicUrl -Encoding UTF8
}

# Update all existing png files at submission root.
$submissionPngFiles = Get-ChildItem -LiteralPath $submissionDirAbs -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -eq ".png" }
if (Test-Path -LiteralPath $qrImageFile) {
    if ($submissionPngFiles.Count -gt 0) {
        foreach ($p in $submissionPngFiles) {
            Copy-Item -LiteralPath $qrImageFile -Destination $p.FullName -Force
        }
    } else {
        Copy-Item -LiteralPath $qrImageFile -Destination $submissionQrFallback -Force
    }
}
Trace "sync_submission_done"

Write-Step "Done"
Trace "script_done"
Write-Host "Backend PID : $($backendProcess.Id)" -ForegroundColor Green
Write-Host "ngrok PID   : $($ngrokProcess.Id)" -ForegroundColor Green
Write-Host "Public URL  : $publicUrl" -ForegroundColor Green
Write-Host "URL file    : $runUrlFile" -ForegroundColor Green
Write-Host "QR file     : $qrImageFile" -ForegroundColor Green
Write-Host "Submission dir      : $submissionDirAbs" -ForegroundColor Green
Write-Host ""
Write-Host "Next run command:" -ForegroundColor Yellow
Write-Host ".\start_public.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "Stable URL example:" -ForegroundColor Yellow
Write-Host ".\start_public.ps1 -NgrokDomain your-fixed-domain.ngrok-free.app" -ForegroundColor Yellow
