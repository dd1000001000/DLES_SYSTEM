# 一键启动 DLES：MySQL（Docker）→ 后端（8080）→ 前端（5173）→ 打开浏览器
# 用法：双击 start.bat，或在 PowerShell 里运行 .\start.ps1 [-NoBrowser]
param([switch]$NoBrowser)

$ErrorActionPreference = 'Continue'
$root = $PSScriptRoot
$backend = Join-Path $root 'dles-backend'
$frontend = Join-Path $root 'dles-frontend\DLES'
$python = Join-Path $backend '.venv\Scripts\python.exe'
$runDir = Join-Path $root '.run'
$mysqlContainer = 'dles-mysql'
$backendPort = 8080
$frontendPort = 5173
$frontendUrl = "http://127.0.0.1:$frontendPort"

function Fail($message) {
    Write-Host "[失败] $message" -ForegroundColor Red
    exit 1
}

function Step($message) { Write-Host "==> $message" -ForegroundColor Cyan }

function Test-Port($port) {
    [bool](Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
}

function Wait-Http($url, $seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 | Out-Null
            return $true
        } catch {
            # 服务已经响应但返回了 4xx/5xx 也算启动成功
            if ($_.Exception.Response) { return $true }
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Start-DlesService($name, $workDir, $command, $pidFile) {
    New-Item -ItemType Directory -Force -Path $runDir | Out-Null
    # cmd /k 让窗口在进程退出后保留，方便看报错；关掉窗口即停止该服务
    $process = Start-Process -FilePath 'cmd.exe' -WorkingDirectory $workDir -PassThru `
        -ArgumentList '/k', "title DLES $name && $command"
    Set-Content -Path (Join-Path $runDir $pidFile) -Value $process.Id
}

# ---- 环境检查 ----
if (-not (Test-Path $python)) { Fail "没有找到后端虚拟环境 $python ，请先按 README 创建 .venv 并安装依赖" }
if (-not (Test-Path (Join-Path $backend '.env'))) { Fail "没有找到 dles-backend\.env ，请先复制 .env.example 并填写" }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Fail '没有找到 npm，请先安装 Node.js' }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail '没有找到 docker，请先安装并启动 Docker Desktop' }

# ---- MySQL ----
Step "检查 MySQL（Docker 容器 $mysqlContainer）"
docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail 'Docker 没有运行，请先启动 Docker Desktop，等它就绪后再运行本脚本' }
$state = docker inspect -f '{{.State.Running}}' $mysqlContainer 2>$null
if ($LASTEXITCODE -ne 0) { Fail "没有找到容器 $mysqlContainer ，请按 README 的“数据库”一节创建" }
if ($state -ne 'true') {
    Write-Host '    容器未运行，正在启动...'
    docker start $mysqlContainer | Out-Null
}
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    docker exec $mysqlContainer mysqladmin ping -h 127.0.0.1 *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) { Fail 'MySQL 60 秒内没有就绪，请用 docker logs dles-mysql 查看原因' }
Write-Host '    MySQL 已就绪'

# ---- 后端 ----
Step "启动后端（http://127.0.0.1:$backendPort）"
if (Test-Port $backendPort) {
    Write-Host '    端口已被占用，认为后端已经在运行，跳过'
} else {
    Start-DlesService 'backend' $backend '.venv\Scripts\python.exe main.py' 'backend.pid'
    if (-not (Wait-Http "http://127.0.0.1:$backendPort/docs" 120)) {
        Fail '后端 120 秒内没有启动成功，请看弹出的“DLES backend”窗口里的报错'
    }
    Write-Host '    后端已就绪'
}

# ---- 前端 ----
Step "启动前端（$frontendUrl）"
if (Test-Port $frontendPort) {
    Write-Host '    端口已被占用，认为前端已经在运行，跳过'
} else {
    if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
        Write-Host '    第一次运行，正在安装前端依赖（npm ci）...'
        Push-Location $frontend
        npm ci
        $installed = $LASTEXITCODE -eq 0
        Pop-Location
        if (-not $installed) { Fail 'npm ci 失败' }
    }
    # 后端的跨域白名单只放行 5173/5174，端口被占用时不要让 vite 悄悄换端口
    Start-DlesService 'frontend' $frontend "npm run dev -- --host 127.0.0.1 --port $frontendPort --strictPort" 'frontend.pid'
    if (-not (Wait-Http $frontendUrl 60)) {
        Fail '前端 60 秒内没有启动成功，请看弹出的“DLES frontend”窗口里的报错'
    }
    Write-Host '    前端已就绪'
}

Write-Host ''
Write-Host "DLES 已启动：$frontendUrl" -ForegroundColor Green
Write-Host '停止：运行 stop.bat（或直接关掉两个 DLES 窗口）'
if (-not $NoBrowser) { Start-Process $frontendUrl }
