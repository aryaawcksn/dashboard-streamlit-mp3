import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(page_title="Dashboard Keuangan Truk Air 2024", layout="wide")

# --- Upload data utama dan lokasi ---
st.sidebar.header("🗂️ Upload Dataset")
uploaded_file = st.sidebar.file_uploader("Unggah file CSV Keuangan", type=["csv"])
lokasi_file = st.sidebar.file_uploader("Unggah file CSV Lokasi", type=["csv"])

if uploaded_file is not None and lokasi_file is not None:
    # --- Load dataset utama dan lokasi ---
    df = pd.read_csv(uploaded_file)
    lokasi_df = pd.read_csv(lokasi_file)

    df.columns = df.columns.str.strip()
    lokasi_df.columns = lokasi_df.columns.str.strip()

    # --- Format tanggal dan tambah kolom Bulan ---
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
    df['Bulan'] = df['Tanggal'].dt.strftime('%Y-%m')

    # --- Bersihkan kolom angka ---
    def clean_currency_column(col):
        return (
            df[col]
            .astype(str)
            .str.replace(r'[^\d,]', '', regex=True)
            .str.replace(',', '')
            .replace('', '0')
            .astype(float)
        )

    df['Jumlah'] = clean_currency_column('Jumlah')
    df['Pengeluaran'] = clean_currency_column('Pengeluaran')
    df['Volume (L)'] = pd.to_numeric(df['Volume (L)'], errors='coerce').fillna(0)
    df['Pemasukan'] = clean_currency_column('Pemasukan')

    # --- Gabungkan data lokasi berdasarkan 'Order' ↔ 'Nama Lokasi' ---
    df['Order'] = df['Order'].astype(str).str.strip().str.lower()
    lokasi_df['Nama Lokasi'] = lokasi_df['Nama Lokasi'].astype(str).str.strip().str.lower()
    df = df.merge(
        lokasi_df[['Nama Lokasi', 'Latitude', 'Longitude']],
        left_on='Order',
        right_on='Nama Lokasi',
        how='left'
    )

    # --- Filter berdasarkan bulan ---
    st.title("📊 Dashboard Keuangan Truk Air 2024")
    bulan_terpilih = st.sidebar.multiselect(
        "Filter Bulan:",
        options=sorted(df['Bulan'].dropna().unique()),
        default=sorted(df['Bulan'].dropna().unique())
    )
    df_filter = df[df['Bulan'].isin(bulan_terpilih)]

    # --- Ringkasan Keuangan (Visual) ---
    st.subheader("1️⃣ Ringkasan Keuangan")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Pemasukan", f"Rp {df_filter['Pemasukan'].sum():,.0f}")
    col2.metric("Total Pengeluaran", f"Rp {df_filter['Pengeluaran'].sum():,.0f}")
    col3.metric("Total Order", f"{df_filter['No'].count()} transaksi")

    st.markdown("📈 **Visualisasi Ringkasan**")
    ringkasan_df = pd.DataFrame({
        "Kategori": ["Pemasukan", "Pengeluaran"],
        "Jumlah (Rp)": [df_filter['Pemasukan'].sum(), df_filter['Pengeluaran'].sum()]
    })

    fig, ax = plt.subplots()
    sns.barplot(data=ringkasan_df, x="Kategori", y="Jumlah (Rp)", palette="Set2", ax=ax)
    ax.set_ylabel("Total dalam Rupiah")
    ax.set_title("Ringkasan Keuangan")
    st.pyplot(fig)

    # --- Pemasukan & Pengeluaran per Bulan ---
    st.subheader("2️⃣ Pemasukan & Pengeluaran per Bulan")
    rekap_bulanan = df_filter.groupby('Bulan').agg({
        'Pemasukan': 'sum',
        'Pengeluaran': 'sum'
    }).sort_index()
    st.line_chart(rekap_bulanan)

    # --- Volume per Bulan ---
    st.subheader("3️⃣ Volume Air Dikirim per Bulan")
    vol_bulanan = df_filter.groupby('Bulan')['Volume (L)'].sum()
    st.bar_chart(vol_bulanan)

    # --- Kinerja Sopir ---
    st.subheader("4️⃣ Kinerja Sopir")
    if 'Sopir' in df_filter.columns:
        sopir_summary = df_filter.groupby('Sopir').agg({
            'No': 'count',
            'Volume (L)': 'sum'
        }).rename(columns={'No': 'Total Order', 'Volume (L)': 'Total Volume'})

        st.dataframe(sopir_summary.sort_values(by='Total Order', ascending=False))

        st.markdown("📊 **Visualisasi Kinerja Sopir**")
        fig, ax = plt.subplots(figsize=(10, 5))
        sopir_sorted = sopir_summary.sort_values(by='Total Order', ascending=False)
        sns.barplot(x=sopir_sorted.index, y=sopir_sorted['Total Order'], color='skyblue', ax=ax)
        ax.set_ylabel("Total Order", color='blue')
        ax.set_xlabel("Sopir")
        ax.tick_params(axis='x', rotation=45)

        ax2 = ax.twinx()
        sns.lineplot(x=sopir_sorted.index, y=sopir_sorted['Total Volume'], color='green', marker='o', ax=ax2)
        ax2.set_ylabel("Total Volume (L)", color='green')

        fig.tight_layout()
        st.pyplot(fig)

    # --- Penggunaan Armada ---
    st.subheader("5️⃣ Penggunaan Armada")
    if 'Plat Nomor' in df_filter.columns:
        armada_summary = df_filter.groupby('Plat Nomor').agg({
            'No': 'count',
            'Pengeluaran': 'sum',
            'Volume (L)': 'mean'
        }).rename(columns={'No': 'Frekuensi', 'Volume (L)': 'Rata-rata Volume'})

        fig, ax1 = plt.subplots(figsize=(10, 5))
        sns.barplot(x=armada_summary.index, y=armada_summary['Frekuensi'], ax=ax1, color='skyblue')
        ax1.set_ylabel("Frekuensi Penggunaan", color='blue')
        ax1.tick_params(axis='x', rotation=45)

        ax2 = ax1.twinx()
        sns.lineplot(x=armada_summary.index, y=armada_summary['Pengeluaran'], ax=ax2, color='red', marker='o')
        sns.lineplot(x=armada_summary.index, y=armada_summary['Rata-rata Volume'], ax=ax2, color='green', marker='s')
        ax2.set_ylabel("Pengeluaran & Rata-rata Volume", color='black')
        fig.tight_layout()
        st.pyplot(fig)

    # --- Peta Lokasi Order + Heatmap ---
    st.subheader("6️⃣ Peta Lokasi Order")
    if 'Latitude' in df_filter.columns and 'Longitude' in df_filter.columns:
        lokasi_valid = df_filter.dropna(subset=['Latitude', 'Longitude'])
        map_center = lokasi_valid[['Latitude', 'Longitude']].mean().tolist() or [-7.8, 110.4]
        m = folium.Map(location=map_center, zoom_start=11)

        for _, row in lokasi_valid.iterrows():
            popup_info = f"""
            <b>{row['Order'].title()}</b><br>
            Volume: {row['Volume (L)']} L<br>
            Pemasukan: Rp {row['Pemasukan']:,.0f}<br>
            Tanggal: {row['Tanggal'].date()}
            """
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=popup_info,
                icon=folium.Icon(color='blue', icon='tint', prefix='fa')
            ).add_to(m)

        # Heatmap berdasarkan volume
        heat_data = lokasi_valid[['Latitude', 'Longitude', 'Volume (L)']].dropna().values.tolist()
        HeatMap(heat_data, radius=15, blur=12, max_zoom=12).add_to(m)

        st_folium(m, width=900, height=500)

    st.caption("Dashboard interaktif untuk eksplorasi data keuangan dan operasional truk air isi ulang 2024.")
else:
    st.info("⬆️ Silakan unggah file CSV keuangan dan lokasi di sidebar untuk memulai.")
