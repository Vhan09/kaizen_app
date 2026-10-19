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
- modules/arsitektur/            predesign dan perhitungan luas/intensitas (ARS-01), ekspor Excel/PDF
- utils/                         fungsi bersama: format angka, penyimpanan, dan tema
- data/mep/                      data dan input MEP dalam format JSON
- data/sipil/                    data Sipil dalam format JSON
- data/arsitektur/               data Arsitektur dalam format JSON

Semua bidang menggunakan satu `app.py`. Untuk penyimpanan bidang baru, gunakan
`utils.storage.load/save/delete(..., domain="sipil")` atau
`utils.storage.load/save/delete(..., domain="arsitektur")`. Pemanggilan lama tanpa
argumen `domain` tetap menggunakan MEP; data MEP lama di `data/` juga tetap dibaca
sebagai fallback dan akan disimpan ke `data/mep/` pada penyimpanan berikutnya.

Modul Arsitektur **Pre-Design** menyediakan laporan Excel dan PDF dengan ringkasan,
parameter proyek, program ruang, kelengkapan form, temuan validasi, dan keputusan
yang tercatat; berita acara Markdown dan data proyek JSON tetap tersedia. Kolom
parameter dan program ruang menyediakan tooltip penjelasan, termasuk acuan katalog;
angka regulasi tetap harus diverifikasi terhadap dokumen resmi setempat.
Alurnya berurutan: **1.1 Tapak**, **1.2 Regulasi** (termasuk perhitungan Luas &
Intensitas), **1.3 Program ruang**, **1.4 Fasad**, **1.5 Produk**, dan
**1.6 Summary**. Pilihan submodel meliputi Perumahan Tapak, Komersil, Mesjid, dan
Gardu; katalog program ruang saat ini masih berupa template perumahan.
Bagian Regulasi menyediakan isian wilayah, Perda/regulasi daerah, dan SNI yang
dirujuk; data tersebut perlu dicatat dari dokumen resmi setempat dan tidak diisi
otomatis. Nilai batas awal pada `data/arsitektur/arsitektur.json` hanya contoh;
hasil pemeriksaan tidak menyatakan kepatuhan hukum. Input perhitungan tersimpan di
`data/arsitektur/luas_bangunan_arsitektur.json`.

Menu Arsitektur **Bukaan & Jendela** menggunakan halaman, perhitungan, data
standar, dan penyimpanan yang sama dengan modul **Kebutuhan Ventilasi** MEP.
