import pandas as pd
import geopandas as gpd
import folium
import numpy as np
import networkx as nx
from pyvis.network import Network
from scipy.spatial.distance import pdist, squareform
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def generate_map(excel_path, shp_path):
    # --- 1. PRA-PEMROSESAN DATA EXCEL ---
    df_geo = pd.read_excel(excel_path, sheet_name='Geografis')
    
    # a. Ekstrak nilai Nasional (baris dengan nama 'INDONESIA')
    # Gunakan .loc lalu .iloc[0] dengan aman, dengan fallback jika tidak ditemukan
    nasional_row = df_geo[df_geo['Prov Kab/Kota'].str.upper() == 'INDONESIA']
    tpt_nasional = nasional_row['TPT 2025'].iloc[0] if not nasional_row.empty else 4.85

    # b. Identifikasi baris Provinsi (Huruf Kapital Semua) dan propagasi data ke bawah (Forward Fill)
    # Kita asumsikan jika nama wilayah semuanya huruf besar (uppercase), itu adalah Provinsi
    df_geo['Is_Provinsi'] = df_geo['Prov Kab/Kota'] == df_geo['Prov Kab/Kota'].str.upper()
    
    # Buat kolom baru untuk menampung data provinsi
    df_geo['Nama Provinsi'] = np.where(df_geo['Is_Provinsi'], df_geo['Prov Kab/Kota'], np.nan)
    df_geo['TPT Provinsi'] = np.where(df_geo['Is_Provinsi'], df_geo['TPT 2025'], np.nan)
    
    # Isi nilai NaN ke bawah dengan nilai provinsi di atasnya
    df_geo['Nama Provinsi'] = df_geo['Nama Provinsi'].ffill()
    df_geo['TPT Provinsi'] = df_geo['TPT Provinsi'].ffill()
    
    # c. Hapus baris agregat (Provinsi dan Nasional) dan hapus duplikat (untuk Papua)
    df_clean = df_geo[~df_geo['Is_Provinsi']].copy()
    df_clean = df_clean[df_clean['Prov Kab/Kota'].str.upper() != 'INDONESIA']
    
    # Tambahkan nilai nasional ke semua baris untuk tooltip
    df_clean['TPT Nasional'] = tpt_nasional

    # --- 2. PENGGABUNGAN DENGAN BENTUK SPASIAL (SHP) ---
    # Asumsi: Kolom nama di file SHP Anda bernama 'WADMKK' (ubah sesuai kolom nama di SHP Anda!)
    gdf_shp = gpd.read_file(shp_path)

    gdf_shp['geometry'] = gdf_shp['geometry'].simplify(tolerance=0.01, preserve_topology=True)
    
    # Lakukan penggabungan (Merge)
    # Pastikan mengubah 'WADMKK' sesuai dengan nama kolom yang berisi nama Kab/Kota di SHP Anda
    gdf_merged = gdf_shp.merge(df_clean, left_on='WADMKK', right_on='Nama_peta_kab', how='inner')
    
    # Pastikan sistem koordinat geografis adalah WGS84 (untuk Folium)
    if gdf_merged.crs is None or gdf_merged.crs.to_string() != 'EPSG:4326':
        gdf_merged = gdf_merged.to_crs(epsg=4326)

    # Menghitung titik tengah (centroid) dari masing-masing wilayah untuk menempatkan titik Symbol Map
    gdf_merged['centroid_lat'] = gdf_merged.geometry.centroid.y
    gdf_merged['centroid_lon'] = gdf_merged.geometry.centroid.x

    # --- 3. MERAKIT PETA FOLIUM ---
    # Inisialisasi peta berpusat di Indonesia
    # m = folium.Map(location=[-2.5, 118.0], zoom_start=5, tiles='cartodbpositron') # Basemap bersih ramah warna
    # m = folium.Map(
    #     location=[-2.5, 118.0], 
    #     zoom_start=5, 
    #     tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    #     attr='Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
    # )
    m = folium.Map(
        location=[-2.5, 118.0], 
        zoom_start=5, 
        tiles='OpenStreetMap'
    )

    # a. Layer 1: Peta Choropleth (Tingkat Pengangguran Terbuka)
    # Membuat format tooltip kustom yang kaya informasi
    tooltip_html = folium.GeoJsonTooltip(
        fields=['Prov Kab/Kota', 'TPT 2025', 'Nama Provinsi', 'TPT Provinsi', 'TPT Nasional'],
        aliases=['Kab/Kota:', 'TPT Kab/Kota (%):', 'Provinsi:', 'Rata-rata Prov (%):', 'Rata-rata Nas (%):'],
        localize=True,
        sticky=False,
        labels=True,
        style="""
            background-color: #F0EFEF;
            border: 1px solid black;
            border-radius: 3px;
            box-shadow: 3px;
        """
    )

    choropleth = folium.Choropleth(
        geo_data=gdf_merged,
        name='Choropleth TPT (Wajib)',
        data=gdf_merged,
        columns=['Prov Kab/Kota', 'TPT 2025'],
        key_on='feature.properties.Prov Kab/Kota',
        fill_color='YlOrRd', # Palet sekuensial yang aman
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Tingkat Pengangguran Terbuka (TPT) 2025 (%)'
    ).add_to(m)

    # Menambahkan tooltip interaktif ke poligon Choropleth
    folium.GeoJson(
        gdf_merged,
        style_function=lambda x: {'fillColor': '#ffffff', 'color':'#000000', 'fillOpacity': 0.1, 'weight': 0.1},
        tooltip=tooltip_html,
        name="Informasi TPT (Tooltip)"
    ).add_to(m)

    # === B. LAYER 2: SYMBOL MAP (TPAK LAKI-LAKI EKSTREM) ===
    layer_tpak_l = folium.FeatureGroup(name='TPAK Laki-laki (Top & Bottom 5)', show=False)
    
    # Ambil 5 Kab/Kota dengan TPAK tertinggi dan 5 terendah
    top5_l = gdf_merged.nlargest(5, 'TPAK 2025 L')
    bot5_l = gdf_merged.nsmallest(5, 'TPAK 2025 L')
    ekstrem_l = pd.concat([top5_l, bot5_l])

    for idx, row in ekstrem_l.iterrows():
        val = row['TPAK 2025 L']
        # Logika visual: 
        # Jika masuk kelompok tertinggi (Top 5), beri warna Biru Gelap dan radius besar
        # Jika masuk kelompok terendah (Bottom 5), beri warna Biru Terang/Pucat dan radius kecil
        is_top = val >= top5_l['TPAK 2025 L'].min()
        
        circle_color = '#08519c' if is_top else '#9ecae1' # Biru gelap vs Biru pucat
        radius_size = 12 if is_top else 5
        label = "Tinggi" if is_top else "Rendah"

        folium.CircleMarker(
            location=[row['centroid_lat'], row['centroid_lon']],
            radius=radius_size,
            popup=f"<b>{row['Prov Kab/Kota']}</b><br>TPAK L: {val}% ({label})",
            tooltip=f"{row['Prov Kab/Kota']} ({label})", # Muncul saat di-hover
            color=circle_color,
            fill=True,
            fill_color=circle_color,
            fill_opacity=0.8
        ).add_to(layer_tpak_l)
    layer_tpak_l.add_to(m)

    # === C. LAYER 3: SYMBOL MAP (TPAK PEREMPUAN EKSTREM) ===
    layer_tpak_p = folium.FeatureGroup(name='TPAK Perempuan (Top & Bottom 5)', show=False)
    
    # Ambil 5 Kab/Kota dengan TPAK tertinggi dan 5 terendah
    top5_p = gdf_merged.nlargest(5, 'TPAK 2025 P')
    bot5_p = gdf_merged.nsmallest(5, 'TPAK 2025 P')
    ekstrem_p = pd.concat([top5_p, bot5_p])

    for idx, row in ekstrem_p.iterrows():
        val = row['TPAK 2025 P']
        is_top = val >= top5_p['TPAK 2025 P'].min()
        
        # Palet Oranye/Merah untuk Perempuan
        circle_color = '#a63603' if is_top else "#ed994f" # Merah/Oranye gelap vs pucat
        radius_size = 12 if is_top else 5
        label = "Tinggi" if is_top else "Rendah"

        folium.CircleMarker(
            location=[row['centroid_lat'], row['centroid_lon']],
            radius=radius_size,
            popup=f"<b>{row['Prov Kab/Kota']}</b><br>TPAK P: {val}% ({label})",
            tooltip=f"{row['Prov Kab/Kota']} ({label})",
            color=circle_color,
            fill=True,
            fill_color=circle_color,
            fill_opacity=0.8
        ).add_to(layer_tpak_p)
    layer_tpak_p.add_to(m)

    # Tambahkan panel kontrol layer (Toggle) - Syarat wajib rubrik
    folium.LayerControl(collapsed=False).add_to(m)

    # Simpan sebagai file HTML statis (sementara, untuk disematkan di web)
    html_output = "templates/peta_indo.html"
    m.save(html_output)
    return True

def generate_network(excel_path):
    df_geo = pd.read_excel(excel_path, sheet_name='Geografis')
    
    # 1. Ambil data agregat Provinsi
    df_geo['Is_Provinsi'] = df_geo['Prov Kab/Kota'] == df_geo['Prov Kab/Kota'].str.upper()
    df_prov = df_geo[df_geo['Is_Provinsi'] & (df_geo['Prov Kab/Kota'] != 'INDONESIA')].copy()
    df_prov = df_prov.dropna(subset=['TPT 2025'])
    
    prov_names = df_prov['Prov Kab/Kota'].tolist()
    tpt_values = df_prov[['TPT 2025']].values
    
    # Persiapan Palet Warna (Hijau ke Merah)
    min_tpt, max_tpt = tpt_values.min(), tpt_values.max()
    cmap = plt.get_cmap('RdYlGn_r') # Reversed Red-Yellow-Green (Tinggi = Merah, Rendah = Hijau)
    norm = mcolors.Normalize(vmin=min_tpt, vmax=max_tpt)

    def get_hex_color(val):
        return mcolors.to_hex(cmap(norm(val)))

    # 2. Hitung Matriks Jarak Euclidean (Selisih TPT)
    dist_matrix = squareform(pdist(tpt_values, metric='euclidean'))
    G = nx.Graph()
    
    # 3. Tambahkan Node dengan Warna berdasarkan TPT
    for i, name in enumerate(prov_names):
        tpt_val = tpt_values[i][0]
        node_color = get_hex_color(tpt_val)
        G.add_node(i, label=name, 
                   title=f"{name} (TPT: {tpt_val}%)",
                   color=node_color)
        
    # 4. Tambahkan Edge dengan Warna Rata-rata TPT
    THRESHOLD = 0.3
    for i in range(len(prov_names)):
        for j in range(i + 1, len(prov_names)):
            selisih = dist_matrix[i, j]
            if selisih <= THRESHOLD:
                bobot = round((THRESHOLD - selisih) * 10, 2)
                # Hitung rata-rata TPT untuk warna garis (edge)
                avg_tpt = (tpt_values[i][0] + tpt_values[j][0]) / 2
                edge_color = get_hex_color(avg_tpt)
                
                G.add_edge(i, j, value=bobot, 
                           color=edge_color, 
                           title=f"Kemiripan kuat (Selisih: {selisih:.2f}%)")

    # 5. Hitung Degree Centrality untuk Ukuran Node
    centrality = nx.degree_centrality(G)
    for node_id in G.nodes():
        G.nodes[node_id]['size'] = (centrality[node_id] * 50) + 10
        # Tambahkan border hitam agar warna node lebih menonjol
        G.nodes[node_id]['borderWidth'] = 1
        G.nodes[node_id]['borderColor'] = '#333333'

    # 6. Render dengan PyVis dan Tweak Mesin Fisika
    net = Network(height='600px', width='100%', bgcolor='#ffffff', font_color='#333333')
    net.from_nx(G)
    
    # Mengubah algoritma tata letak agar menyebar lebih organik
    net.force_atlas_2based(
        gravity=-50,
        central_gravity=0.01,
        spring_length=100,
        spring_strength=0.08,
        damping=0.4
    )
    
    html_output = "templates/network_indo.html"
    net.save_graph(html_output)
    
    return True