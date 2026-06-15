Write-Host ""
Write-Host "  Cloudflare Tunnel wird gestartet..." -ForegroundColor Yellow
Write-Host "  Warte auf oeffentliche URL..." -ForegroundColor Gray
Write-Host ""

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "$PSScriptRoot\cloudflared.exe"
$psi.Arguments = "tunnel --url http://localhost:5173"
$psi.UseShellExecute = $false
$psi.RedirectStandardError = $true
$psi.RedirectStandardOutput = $true

$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
$p.Start() | Out-Null

$url = $null

while (-not $p.StandardError.EndOfStream) {
    $line = $p.StandardError.ReadLine()
    Write-Host "  $line" -ForegroundColor DarkGray

    if ($line -match "(https://[a-z0-9\-]+\.trycloudflare\.com)") {
        $url = $Matches[1]

        Write-Host ""
        Write-Host "  ========================================" -ForegroundColor Green
        Write-Host "   Tunnel aktiv!" -ForegroundColor Green
        Write-Host "   $url" -ForegroundColor Cyan
        Write-Host "  ========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "  Warte 8 Sekunden bis DNS aktiv ist..." -ForegroundColor Yellow

        # DNS braucht ein paar Sekunden
        for ($i = 8; $i -gt 0; $i--) {
            Write-Host "  $i..." -ForegroundColor DarkGray -NoNewline
            Start-Sleep -Seconds 1
        }
        Write-Host ""

        Write-Host ""
        Write-Host "  Browser wird geoeffnet..." -ForegroundColor Yellow
        Start-Process $url
        Write-Host ""
        Write-Host "  Diese URL mit anderen teilen:" -ForegroundColor Cyan
        Write-Host "  $url" -ForegroundColor White
        Write-Host ""
        Write-Host "  Fenster offen lassen solange die App lauft." -ForegroundColor Gray
        Write-Host ""
        break
    }
}

# Weiter lesen damit Tunnel laeuft
while (-not $p.StandardError.EndOfStream) {
    $line = $p.StandardError.ReadLine()
    if ($line -match "error|ERR|failed" -and $line -notmatch "debug") {
        Write-Host "  $line" -ForegroundColor Red
    }
}

$p.WaitForExit()
Write-Host "  Tunnel beendet." -ForegroundColor Yellow
