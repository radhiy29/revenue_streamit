import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import google.generativeai as genai
import os

# ======== SETTING API GEMINI =========
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
if GEMINI_API_KEY and GEMINI_API_KEY.strip():
    genai.configure(api_key=GEMINI_API_KEY)
    model_gemini = genai.GenerativeModel("gemini-2.5-flash")  
else:
    print("⚠️ GEMINI_API_KEY belum diatur! Gunakan export/set di terminal atau ganti default value.")
    model_gemini = None

PRODUCT_OPTIONS = ["Semua Produk", "INDIBIZ", "INDIHOME", "Wifi Managed Service", "WMS", "WMS LITE"]

def tampilkan_visualisasi(df: pd.DataFrame, periode: str = "Harian"):
    df = df.copy()
    df.columns = df.columns.str.strip().str.upper()

    if 'TANGGAL' not in df.columns:
        st.error("Kolom 'TANGGAL' tidak ditemukan dalam data.")
        return
    df['TANGGAL'] = df['TANGGAL'].astype(str).str.slice(0, 8)
    df['TANGGAL'] = pd.to_datetime(df['TANGGAL'], format='%Y%m%d', errors='coerce')
    df = df.dropna(subset=['TANGGAL'])

    # =============== FILTER DI SIDEBAR ===============
    with st.sidebar:
        st.markdown("### 🔧 Filter Data")

        # Filter daerah
        if 'TELKOM_DAERAH' in df.columns:
            df['TELKOM_DAERAH'] = df['TELKOM_DAERAH'].astype(str).str.strip()
            daerah_unik = sorted(df['TELKOM_DAERAH'].unique())
            opsi_daerah = ["Semua Daerah"] + daerah_unik
            pilihan_daerah = st.multiselect(
                "Pilih Daerah:",
                options=opsi_daerah,
                default=["Semua Daerah"],
                key=f"daerah_{periode.lower()}"
            )
            if "Semua Daerah" not in pilihan_daerah:
                df = df[df['TELKOM_DAERAH'].isin(pilihan_daerah)]

        # Filter produk (multi pilih)
        nama_produk_untuk_judul = "Semua Produk"
        if 'PRODUCT' in df.columns:
            df['PRODUCT'] = df['PRODUCT'].astype(str).str.strip()
            produk_unik = sorted(df['PRODUCT'].unique())
            opsi_produk = ["Semua Produk"] + produk_unik
            pilihan_produk = st.multiselect(
                "Pilih Produk:",
                options=opsi_produk,
                default=["Semua Produk"],
                key=f"produk_{periode.lower()}"
            )
            if "Semua Produk" not in pilihan_produk and len(pilihan_produk) > 0:
                df = df[df['PRODUCT'].str.upper().isin([p.upper() for p in pilihan_produk])]
                nama_produk_untuk_judul = ", ".join(pilihan_produk)

        # Mode tampilan data
        pilihan_tampilan = st.radio(
            "Pilih Tampilan Data:",
            options=["Semua Data", "Filter Rentang Tanggal"],
            key=f"mode_{periode.lower()}"
        )
        if pilihan_tampilan == "Filter Rentang Tanggal":
            min_date = df['TANGGAL'].min().date()
            max_date = df['TANGGAL'].max().date()
            start_date, end_date = st.date_input(
                "Pilih rentang tanggal:",
                value=[min_date, max_date],
                min_value=min_date,
                max_value=max_date,
                key=f"tanggal_{periode.lower()}"
            )
            df = df[(df['TANGGAL'] >= pd.to_datetime(start_date)) &
                    (df['TANGGAL'] <= pd.to_datetime(end_date))]

        # Opsional MA7
        tampilkan_ma = False
        if periode.lower() == "harian":
            tampilkan_ma = st.checkbox(
                "Tampilkan Moving Average 7 Hari",
                value=False,
                key=f"ma7_{periode.lower()}"
            )

    # =================================================

    if 'REV_PACKAGE' not in df.columns:
        st.error("Kolom 'REV_PACKAGE' tidak ditemukan dalam data.")
        return
    df['REV_PACKAGE'] = df['REV_PACKAGE'].fillna(0)

    # Resample sesuai periode
    if periode.lower() == "harian":
        resample_rule = "D"
        tanggal_format_tabel = "%Y-%m-%d"
        tanggal_format_grafik = "%d-%m-%y"
    elif periode.lower() == "mingguan":
        resample_rule = "W-MON"
        tanggal_format_tabel = "%Y-%m-%d"
        tanggal_format_grafik = "%d-%m-%y"
    elif periode.lower() == "bulanan":
        resample_rule = "MS"
        tanggal_format_tabel = "%Y-%m"
        tanggal_format_grafik = "%Y-%m"
    else:
        st.error("Periode tidak valid, gunakan 'Harian', 'Mingguan', atau 'Bulanan'.")
        return

    try:
        df_aggr = df.resample(resample_rule, on='TANGGAL')['REV_PACKAGE'].sum().reset_index()
    except Exception as e:
        st.error(f"Gagal melakukan agregasi dengan rule {resample_rule}: {e}")
        return

    try:
        date_range = pd.date_range(
            start=df_aggr['TANGGAL'].min(),
            end=df_aggr['TANGGAL'].max(),
            freq=resample_rule
        )
        df_full = pd.DataFrame({'TANGGAL': date_range})
        df_final = pd.merge(df_full, df_aggr, on='TANGGAL', how='left')
        df_final['REV_PACKAGE'] = df_final['REV_PACKAGE'].fillna(0)
    except Exception:
        df_final = df_aggr.copy()

    if periode.lower() == "harian" and tampilkan_ma:
        df_final['MA7'] = df_final['REV_PACKAGE'].rolling(window=7, min_periods=1).mean()

    # ========== TAMPILKAN TABEL ==========
    df_tabel = df_final.copy()
    # ganti nama kolom REV_PACKAGE menjadi REVENUE untuk user
    df_tabel = df_tabel.rename(columns={"REV_PACKAGE": "REVENUE"})
    if periode.lower() == "harian":
        df_tabel['TANGGAL'] = df_tabel['TANGGAL'].dt.strftime(tanggal_format_tabel)
    elif periode.lower() == "mingguan":
        df_tabel['TANGGAL'] = df_tabel['TANGGAL'].dt.date
    elif periode.lower() == "bulanan":
        df_tabel['TANGGAL'] = df_tabel['TANGGAL'].dt.strftime(tanggal_format_tabel)
    df_tabel.index = range(1, len(df_tabel) + 1)

    st.markdown(f"<h3 style='text-align: center;'>📋 Data Revenue {nama_produk_untuk_judul} {periode.capitalize()}</h3>", unsafe_allow_html=True)
    st.dataframe(df_tabel, use_container_width=True)

    # Download CSV
    nama_file_csv = f"revenue_{periode.lower()}_{nama_produk_untuk_judul.replace(' ', '_').lower()}.csv"
    csv_data = df_tabel.to_csv(index=True, encoding='utf-8-sig')
    st.download_button(
        label="💾 Download CSV",
        data=csv_data,
        file_name=nama_file_csv,
        mime="text/csv"
    )

    # ========== TAMPILKAN GRAFIK ==========
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_final['TANGGAL'],
        y=df_final['REV_PACKAGE'],
        mode='lines+markers' if periode.lower() != "harian" else 'lines',
        name=f"Revenue {periode.capitalize()}",
        hovertemplate=f'<b>Periode</b>: %{{x|{tanggal_format_grafik}}}<br><b>Revenue</b>: %{{y:,.0f}}<extra></extra>'
    ))
    if periode.lower() == "harian" and 'MA7' in df_final.columns:
        fig.add_trace(go.Scatter(
            x=df_final['TANGGAL'],
            y=df_final['MA7'],
            mode='lines',
            name='MA 7 Hari',
            line=dict(width=2, dash='dot', color='orange'),
            hovertemplate=f'<b>Periode</b>: %{{x|{tanggal_format_grafik}}}<br><b>MA7</b>: %{{y:,.0f}}<extra></extra>'
        ))

    if len(df_final) > 0:
        first_date = df_final['TANGGAL'].min()
        last_date = df_final['TANGGAL'].max()
        if periode.lower() == "harian":
            x_range = [first_date - pd.Timedelta(days=3), last_date + pd.Timedelta(days=3)]
        elif periode.lower() == "mingguan":
            x_range = [pd.to_datetime(first_date) - pd.Timedelta(days=7), pd.to_datetime(last_date) + pd.Timedelta(days=7)]
        else:
            x_range = [first_date - pd.DateOffset(days=15), last_date + pd.DateOffset(days=15)]
    else:
        x_range = None

    fig.update_layout(
        xaxis_title='Periode',
        yaxis_title='Total Revenue',   # <<== diubah label Y
        xaxis=dict(tickformat=tanggal_format_grafik, range=x_range, showgrid=True),
        yaxis=dict(tickformat=",", showgrid=True),
        margin=dict(l=50, r=50, t=80, b=50),
        hovermode='x unified',
        template='plotly_white'
    )

    st.markdown("---")
    st.markdown(f"<h3 style='text-align: center;'>📊 Grafik Revenue {nama_produk_untuk_judul} {periode.capitalize()}</h3>", unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)

    # Download grafik HTML (interaktif)
    html_file = f"grafik_revenue_{periode.lower()}_{nama_produk_untuk_judul.replace(' ', '_').lower()}.html"
    html_data = fig.to_html(full_html=True, include_plotlyjs='cdn')
    st.download_button(
        label="🌐 Download Grafik Interaktif (HTML)",
        data=html_data,
        file_name=html_file,
        mime="text/html"
    )

    # ========== ANALISIS GEMINI ==========
    if model_gemini:
        st.markdown("---")
        st.markdown("<h3 style='text-align: center;'>🤖 Analisis dengan Gemini</h3>", unsafe_allow_html=True)
      
        pakai_gemini = st.checkbox("Aktifkan Analisis Otomatis", value=False, key=f"gemini_{periode.lower()}")
        if pakai_gemini:
            try:
                summary_data = {
                    "total_revenue": float(df_final['REV_PACKAGE'].sum()),
                    "rata_rata": float(df_final['REV_PACKAGE'].mean()),
                    "maksimum": float(df_final['REV_PACKAGE'].max()),
                    "tanggal_maks": str(df_final.loc[df_final['REV_PACKAGE'].idxmax(), 'TANGGAL']),
                    "minimum": float(df_final['REV_PACKAGE'].min()),
                    "tanggal_min": str(df_final.loc[df_final['REV_PACKAGE'].idxmin(), 'TANGGAL']),
                }
                if 'PRODUCT' in df.columns:
                    summary_data["produk_teratas"] = df.groupby('PRODUCT')['REV_PACKAGE'].sum().sort_values(ascending=False).head(3).to_dict()
                if 'TELKOM_DAERAH' in df.columns:
                    summary_data["daerah_teratas"] = df.groupby('TELKOM_DAERAH')['REV_PACKAGE'].sum().sort_values(ascending=False).head(3).to_dict()

                prompt = f"""
                Analisislah data revenue berikut:
                {summary_data}

                Buat ringkasan berisi:
                1. Gambaran umum
                2. Tren pergerakan
                3. Perbandingan produk (jika ada)
                4. Perbandingan daerah (jika ada)
                5. Insight & Rekomendasi
                """
                response = model_gemini.generate_content(prompt)
                hasil = response.text

                st.write(hasil)
            except Exception as e:
                st.error(f"Gagal memproses analisis Gemini: {e}")
