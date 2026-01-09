import sys
import os
import streamlit.web.cli as stcli

def main():
    # PyInstaller çalıştığında geçici klasör yolunu (_MEIPASS) kullanır
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    # Uygulama dosyamızın tam yolu
    app_path = os.path.join(base_path, 'src', 'app.py')

    # Streamlit komut satırı argümanlarını simüle et
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        "--server.headless=true",
    ]
    
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
