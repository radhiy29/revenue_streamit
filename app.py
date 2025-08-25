# app.py
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
import google.generativeai as genai
from visualisasi.logic import tampilkan_visualisasi

# ======== KONFIGURASI GEMINI =========
load_dotenv()  # baca file .env
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.warning("⚠️ GEMINI_API_KEY tidak ditemukan di file .env")

# ======== STREAMLIT APP =========
st.set_page_config(page_title="Visualisasi Revenue", layout="wide")
st.title("📊 Dashboard Revenue Indibiz")

# Fungsi baca file
def baca_file_data(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith((".xls", ".xlsx")):
        return pd.read_excel(uploaded_file, engine="openpyxl")
    else:
        st.error("Format file tidak didukung.")
        return None

# ======== SIDEBAR ========
st.sidebar.header("⚙️ Pengaturan")

uploaded = st.sidebar.file_uploader("📂 Unggah file CSV/Excel", type=["csv", "xlsx"])

menu = st.sidebar.radio(
    "Pilih Jenis Visualisasi:",
    ["Per Hari", "Per Minggu", "Per Bulan"]
)

# ======== MAIN CONTENT ========
if uploaded:
    df = baca_file_data(uploaded)
    if df is not None:
        if menu == "Per Hari":
            tampilkan_visualisasi(df, periode="Harian")
        elif menu == "Per Minggu":
            tampilkan_visualisasi(df, periode="Mingguan")
        elif menu == "Per Bulan":
            tampilkan_visualisasi(df, periode="Bulanan")
else:
    st.info("Silakan unggah file terlebih dahulu dari sidebar.")
