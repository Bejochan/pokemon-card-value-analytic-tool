// Konfigurasi dinamis alamat Backend API Regokemon
// Menggunakan environment variable VITE_API_BASE_URL jika tersedia (misal di Vercel),
// atau fallback ke http://127.0.0.1:8000 untuk pengujian lokal.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

