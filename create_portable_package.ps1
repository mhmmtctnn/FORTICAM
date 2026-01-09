# create_portable_package.ps1
# FortiManager Controller icin Portable Paket Olusturucu
# Yontem: Python Embeddable Package Kullanimi

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$pythonVersion = "3.11.9"
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip"
$pipUrl = "https://bootstrap.pypa.io/get-pip.py"
$distDir = "dist_portable"
$pythonDir = "$distDir\python"

Write-Host ">>> FortiController Portable Paket Olusturuluyor..." -ForegroundColor Cyan

# 1. Klasorleri Hazirla
if (Test-Path $distDir) { Remove-Item -Recurse -Force $distDir }
New-Item -ItemType Directory -Path $pythonDir | Out-Null
New-Item -ItemType Directory -Path "$distDir\app" | Out-Null

# 2. Kaynak Kodlari Kopyala
Write-Host ">>> Kaynak kodlar kopyalaniyor..." -ForegroundColor Yellow
Copy-Item -Recurse "src" "$distDir\app\src"
Copy-Item "requirements.txt" "$distDir\app\"
Copy-Item "run_portable.py" "$distDir\app\" # run_portable.py'yi de kopyala

# 3. Python Embeddable Indir ve Ac
Write-Host ">>> Python $pythonVersion indiriliyor..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $pythonUrl -OutFile "python.zip"
Expand-Archive -Path "python.zip" -DestinationPath $pythonDir
Remove-Item "python.zip"

# 4. python311._pth dosyasini duzenle (import site destegi icin)
# 'import site' satiri yorumdan cikarilmali ki pip calissin.
$pthFile = "$pythonDir\python311._pth"
$content = Get-Content $pthFile
$content = $content -replace "#import site", "import site"
$content | Set-Content $pthFile

# 5. Pip Kurulumu
Write-Host ">>> Pip kuruluyor..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $pipUrl -OutFile "$pythonDir\get-pip.py"
& "$pythonDir\python.exe" "$pythonDir\get-pip.py" --no-warn-script-location
Remove-Item "$pythonDir\get-pip.py"

# 6. Bagimliliklari Kur
Write-Host ">>> Kutuphaneler yukleniyor (Bu biraz surebilir)..." -ForegroundColor Yellow
# Pip Scripts klasorunde oldugu icin path'e eklemek yerine direkt cagiriyoruz
$pipExe = "$pythonDir\Scripts\pip.exe"
& $pipExe install -r "$distDir\app\requirements.txt" --no-warn-script-location

# 7. Baslatici BAT Dosyasi Olustur
Write-Host ">>> Baslatma dosyasi olusturuluyor..." -ForegroundColor Yellow
$batContent = @"
@echo off
title FortiManager Controller
echo Baslatiliyor... Lutfen bekleyin...

:: Portable Python ile baslat
"%~dp0python\python.exe" "%~dp0app\run_portable.py"

if %errorlevel% neq 0 (
    echo.
    echo Bir hata olustu! Pencereyi kapatmadan once hatayi okuyun.
    pause
)
"@
Set-Content -Path "$distDir\BASLAT.bat" -Value $batContent

Write-Host ""
Write-Host ">>> ISLEM TAMAMLANDI! <<<" -ForegroundColor Green
Write-Host "Olusturulan klasor: $distDir"
Write-Host "Bu klasoru ($distDir) istediginiz bilgisayara tasiyabilirsiniz."
Write-Host "Calistirmak icin icindeki 'BASLAT.bat' dosyasina tiklayin."
