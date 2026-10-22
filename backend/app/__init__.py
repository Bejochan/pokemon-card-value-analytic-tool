"""
backend/app/__init__.py
Inisialisasi package backend Regokemon.
Memastikan dependensi PyTorch dan OpenMP termuat secara aman pada OS Windows
sebelum modul machine learning lain (Scikit-Learn, Joblib, OpenCV) diinisialisasi.
"""

import os
import sys

# Mencegah konflik OpenMP libiomp5md di Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Mencegah fragmentasi VRAM CUDA di PyTorch (penting untuk GPU 4GB)
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Inisialisasi awal PyTorch
try:
    import torch
except Exception:
    pass

