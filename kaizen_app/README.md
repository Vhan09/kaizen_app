# Kaizen PBG

## Jalankan (Windows, di terminal VS Code)
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app.py

## Struktur
- app.py                         menu + halaman utama
- modules/beban_listrik*.py      Modul 1 (view, kalkulasi, tabel HTML)
- modules/akli*.py               Tabel AKLI + aturan kabel otomatis
- utils/                         format angka, simpan data, tema
- data/                          data input tersimpan otomatis (JSON)
