@echo off
echo FortiManager Controller Build Islemi Baslatiliyor...
echo Bu islem birkac dakika surebilir. Lutfen bekleyin...

:: PyInstaller Build Komutu
python -m PyInstaller --noconfirm --onedir --windowed --clean ^
 --name "FortiController" ^
 --add-data "src;src" ^
 --add-data ".streamlit;.streamlit" ^
 --hidden-import "pandas" ^
 --hidden-import "altair" ^
 --hidden-import "streamlit" ^
 --collect-all "streamlit" ^
 --collect-all "altair" ^
 --collect-all "pandas" ^
 run_portable.py

echo.
echo Islem Tamamlandi!
echo Olusturulan dosyalar "dist\FortiController" klasorundedir.
pause
