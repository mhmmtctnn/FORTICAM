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
