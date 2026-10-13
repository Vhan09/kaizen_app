# Kaizen PBG

## Jalankan (Windows, di terminal VS Code)
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app.py

## Struktur
- app.py                         halaman utama dan pemilih bidang
- modules/mep/                   modul perhitungan Mechanical, Electrical, Plumbing
- modules/sipil/                 modul perhitungan bidang Sipil
- modules/arsitektur/            modul perhitungan bidang Arsitektur
- utils/                         fungsi bersama: format angka, penyimpanan, dan tema
- data/mep/                      data dan input MEP dalam format JSON
- data/sipil/                    data Sipil dalam format JSON
- data/arsitektur/               data Arsitektur dalam format JSON

Semua bidang menggunakan satu `app.py`. Untuk penyimpanan bidang baru, gunakan
`utils.storage.load/save/delete(..., domain="sipil")` atau
`utils.storage.load/save/delete(..., domain="arsitektur")`. Pemanggilan lama tanpa
argumen `domain` tetap menggunakan MEP; data MEP lama di `data/` juga tetap dibaca
sebagai fallback dan akan disimpan ke `data/mep/` pada penyimpanan berikutnya.
