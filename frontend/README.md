# Frontend - Regokemon (Web Portal)

Antarmuka web interaktif untuk sistem analitika dan valuasi kartu Pokémon berbasis React 19 dan Vite.

---

## 📌 Halaman & Fitur Utama

Frontend Regokemon terdiri dari beberapa halaman dan komponen inti:

1. **Catalog (`CatalogPage.jsx`)**
   * Penjelajahan 20.617 kartu Pokémon resmi.
   * Pencarian instan berdasarkan nama kartu, filter set (172 ekspansi), supertype (Pokémon, Trainer, Energy), dan tingkat kelangkaan (*rarity*).
   * Modal pratinjau kartu untuk melihat detail atribut dan riwayat harga.

2. **Live Scanner HUD & Upload (`UploadPage.jsx`)**
   * **Mode Live Camera:** Pemindaian langsung via webcam atau kamera smartphone (DroidCam) dengan panduan rasio kartu 63:88, indikator ketajaman sensor, serta telemetri FPS dan latensi.
   * **Mode Upload Foto:** Unggah foto dua sisi (tampak depan dan belakang) dengan kompresi otomatis HTML5 Canvas (maksimal 1280px) untuk memangkas ukuran payload HTTP sebelum dikirim ke backend.

3. **Dashboard Analitik & Hasil Pemindaian (`ScannerDashboard.jsx` & `DashboardPage.jsx`)**
   * **Identifikasi Kartu:** Menampilkan kartu teridentifikasi hasil pencocokan Model 1 (CLIP ViT-B/32 + FAISS + ORB).
   * **Inspeksi Kondisi Fisik:** Visualisasi cacat fisik (goresan permukaan, kikisan tepi dan sudut) hasil deteksi Model 2 (YOLOv8) beserta persentase potongan harga.
   * **Grafik Tren & Peramalan 7 Hari:** Kurva harga historis bersambung dengan proyeksi probabilistik Model 3 (Amazon Chronos-Bolt) yang dilengkapi pita kuantil P10, P50, dan P90.
   * **Sinyal Transaksi:** Rekomendasi preskriptif **BUY**, **HOLD**, atau **SELL** berdasarkan posisi harga listing terhadap lorong harga wajar.

---

## 🚀 Panduan Menjalankan Frontend

### Persyaratan Sistem:
* **Node.js:** Versi 18.0 atau lebih baru
* **npm:** Versi 9.0 atau lebih baru

### 1. Instalasi Dependensi
Jalankan perintah berikut di dalam direktori `frontend`:
```bash
cd frontend
npm install
```

### 2. Konfigurasi Environment Variable
Frontend berkomunikasi dengan backend FastAPI melalui variabel lingkungan. Buat berkas `.env` di folder `frontend/` jika ingin mengubah alamat backend:

```env
# Alamat REST API Backend FastAPI (default lokal)
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Jika berkas `.env` tidak disediakan, aplikasi secara otomatis menggunakan `http://127.0.0.1:8000`.

### 3. Menjalankan Server Pengembangan (Dev Mode)
```bash
npm run dev
```
Akses aplikasi melalui peramban di: **`http://localhost:5173`**

### 4. Build untuk Produksi
```bash
npm run build
```
Hasil kompilasi produksi akan tersimpan di direktori `frontend/dist/` dan siap dideploy ke platform hosting statis seperti Vercel.

---

## 🛠️ Struktur Komponen Frontend

```text
frontend/
├── public/                 # Aset statis (logo, ikon, gambar latar)
├── src/
│   ├── assets/             # Aset gambar komponen React
│   ├── components/
│   │   ├── Navbar.jsx          # Navigasi utama aplikasi
│   │   ├── HeroSection.jsx     # Banner beranda dan aksi mulai scan
│   │   ├── CatalogPage.jsx     # Katalog interaktif 20.617 kartu
│   │   ├── UploadPage.jsx      # Upload foto statis & Live Camera HUD
│   │   ├── ScannerDashboard.jsx# Hasil identifikasi, cacat, & grafik Chronos
│   │   ├── DashboardPage.jsx   # Agregasi analitika pasar & tren global
│   │   └── Marketplace.jsx     # Simulasi jual beli kartu lokal
│   ├── config/
│   │   └── api.js              # Resolusi BASE_URL backend
│   ├── App.jsx             # Pengatur navigasi halaman
│   ├── main.jsx            # Entrypoint ReactDOM
│   └── index.css           # Styling dasar global
├── package.json
└── vite.config.js
```
