# Windows PowerShell 5.1+. Run as a normal user.
# This launches a local-only WSGI backend; Tailscale Serve is enabled once
# separately in an elevated terminal. Never expose this via Tailscale Funnel.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$project = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $project

function Find-Program([string]$name, [string]$fallback) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    if (Test-Path $fallback) { return $fallback }
    throw ("Не найдена программа " + $name + ". Установите её и повторите запуск.")
}

$tailscale = Find-Program "tailscale" (Join-Path $env:ProgramFiles "Tailscale\tailscale.exe")
$uv = Find-Program "uv" (Join-Path $env:USERPROFILE ".local\bin\uv.exe")

$statusJson = (& $tailscale status --json | Out-String)
if ($LASTEXITCODE -ne 0) {
    throw "Tailscale не подключён. Откройте Tailscale и войдите в учётную запись."
}
$status = $statusJson | ConvertFrom-Json
if ($status.BackendState -ne "Running" -or -not $status.Self -or -not $status.Self.DNSName) {
    throw "Tailscale не подключён к сети. Проверьте вход и состояние приложения."
}
$dnsName = ([string]$status.Self.DNSName).TrimEnd(".")
if (-not $dnsName.EndsWith(".ts.net", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Не удалось определить личный HTTPS-адрес Tailscale. Проверьте MagicDNS."
}

# Scope production-like security settings to only this application process.
$env:DJANGO_SETTINGS_MODULE = "config.settings.production"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,$dnsName"
$env:DJANGO_CSRF_TRUSTED_ORIGINS = "https://$dnsName"
$env:DJANGO_DEBUG = "false"

# Keep a stable high-entropy Django session key across restarts.
$envPath = Join-Path $project ".env"
$existing = if (Test-Path $envPath) { [System.IO.File]::ReadAllText($envPath) } else { "" }
$expression = [regex]::new("(?m)^\s*DJANGO_SECRET_KEY\s*=\s*(.*?)\s*$")
$match = $expression.Match($existing)
$secret = if ($match.Success) { $match.Groups[1].Value.Trim().Trim([char[]]@('"', "'")) } else { "" }
if ($secret.Length -lt 32 -or $secret -match "dev-only|замените|change.me|placeholder|^<") {
    $bytes = New-Object byte[] 48
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    $secret = [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+","-").Replace("/","_")
    if ($match.Success) {
        $existing = $expression.Replace($existing, "DJANGO_SECRET_KEY=$secret", 1)
    } else {
        $existing = $existing.TrimEnd([char[]]@(13,10)) + [Environment]::NewLine +
            "DJANGO_SECRET_KEY=$secret" + [Environment]::NewLine
    }
    [System.IO.File]::WriteAllText(
        $envPath, $existing, (New-Object System.Text.UTF8Encoding($false))
    )
    Write-Host "Создан безопасный постоянный DJANGO_SECRET_KEY в .env"
}

Write-Host ""
Write-Host "Готовим Django для приватного запуска..."
& $uv sync
if ($LASTEXITCODE -ne 0) { throw "uv sync завершился ошибкой." }
& $uv run python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "Не удалось обновить структуру базы данных." }
& $uv run python manage.py load_content
if ($LASTEXITCODE -ne 0) { throw "Не удалось загрузить учебные материалы." }
& $uv run python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) { throw "Не удалось подготовить CSS и JS." }
& $uv run python manage.py check --deploy
if ($LASTEXITCODE -ne 0) { throw "Проверка Django не прошла." }

Write-Host ""
Write-Host "Личный адрес сайта: https://$dnsName/"
Write-Host "Для первоначальной настройки откройте ОТДЕЛЬНЫЙ Windows Terminal (Администратор):"
Write-Host "  tailscale serve --bg 8000"
Write-Host "Проверка: tailscale serve status"
Write-Host ""
Write-Host "Запуск приватного приложения на 127.0.0.1:8000 через Waitress."
Write-Host "Оставьте окно открытым; для остановки нажмите Ctrl+C."
Write-Host "Не используйте tailscale funnel для этого частного сайта."
Write-Host ""
& $uv run --with "waitress>=3.0,<4" waitress-serve --listen=127.0.0.1:8000 --url-scheme=https config.wsgi:application
if ($LASTEXITCODE -ne 0) { throw "Приложение не запустилось. Проверьте вывод выше." }
