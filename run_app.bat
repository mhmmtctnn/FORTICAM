@echo off
title FortiManager Controller - Portable Launcher
echo ---------------------------------------------------
echo      FortiManager Interface Controller
echo ---------------------------------------------------
echo.

:: 1. Docker Kontrolü
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Docker bulunamadi! Lutfen once Docker Desktop'i kurun.
    pause
    exit
)

:: 2. Imaj Kontrolü ve Yukleme
docker image inspect forticam-fortimanager-app >nul 2>&1
if %errorlevel% neq 0 (
    if exist "forticam_image.tar" (
        echo [BILGI] Uygulama imaji yukleniyor (Bu islem bir kez yapilir)...
        docker load -i forticam_image.tar
        echo [BASARILI] Imaj yuklendi.
    ) else (
        echo [HATA] 'forticam_image.tar' dosyasi bulunamadi!
        pause
        exit
    )
) else (
    echo [BILGI] Uygulama imaji zaten yuklu.
)

:: 3. Uygulamayi Baslatma
echo.
echo [BILGI] Uygulama baslatiliyor...
echo.
echo Lutfen bekleyin, tarayici otomatik acilacak...

start "" "http://localhost:8501"
docker-compose up -d

if %errorlevel% neq 0 (
    echo [HATA] Baslatma sirasinda bir sorun olustu.
    pause
) else (
    echo.
    echo [BASARILI] Uygulama arka planda calisiyor.
    echo Kapatmak icin Docker Desktop'tan konteyneri durdurabilirsiniz.
    timeout /t 5
)
