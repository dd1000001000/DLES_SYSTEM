# 停止 DLES 的后端和前端；加 -Db 会连 MySQL 容器一起停掉
param([switch]$Db)

$runDir = Join-Path $PSScriptRoot '.run'

function Stop-Tree($processId) {
    if ($processId) { taskkill /PID $processId /T /F *> $null }
}

foreach ($name in 'backend', 'frontend') {
    $pidFile = Join-Path $runDir "$name.pid"
    if (Test-Path $pidFile) {
        Stop-Tree ([int](Get-Content $pidFile))
        Remove-Item $pidFile
    }
}

# 不是用 start.ps1 启动的（或 pid 文件丢了），按端口兜底
foreach ($port in 8080, 5173) {
    Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Tree $_.OwningProcess }
}
Write-Host '后端和前端已停止'

if ($Db) {
    docker stop dles-mysql | Out-Null
    Write-Host 'MySQL 容器已停止'
}
