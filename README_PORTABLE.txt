FORTIMANAGER INTERFACE CONTROLLER - PORTABLE VERSION
======================================================

Bu klasör, uygulamayı baska bir bilgisayarda calistirmak icin gerekli dosyalari icerir.

GEREKSINIMLER:
--------------
- Hedef bilgisayarda "Docker Desktop" kurulu ve calisiyor olmalidir.

KURULUM VE CALISTIRMA:
----------------------
1. Bu klasörü hedef bilgisayara kopyalayin.
2. "run_app.bat" dosyasina cift tiklayin.
3. Script otomatik olarak:
   - Docker imajini sisteme yukleyecek (ilk seferde).
   - Uygulamayi baslatacak.
   - Tarayicinizda (http://localhost:8501) arayuzu acacak.

DOSYA ICERIGI:
--------------
- run_app.bat         -> Calistirma scripti (Windows).
- forticam_image.tar  -> Uygulama imaji (Silmeyin).
- docker-compose.yml  -> Konfigurasyon dosyasi.
- .streamlit/         -> Arayuz ayarlari (Opsiyonel).

NOT:
----
Uygulamayi kapatmak icin Docker Desktop uzerinden "fortimanager_controller" konteynerini durdurabilir veya silebilirsiniz.
