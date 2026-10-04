from flask import Flask, render_template
import pandas as pd
import plotly.express as px
import plotly.utils
import json
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import plotly.graph_objects as go
import networkx as nx
from scipy.spatial.distance import pdist, squareform
import matplotlib.colors as mcolors

app = Flask(__name__)

def prepare_icicle_data():
    df_h1 = pd.read_excel('data.xlsx', sheet_name='Hirarki 1')
    
    df_h1.set_index(df_h1.columns[0], inplace=True)
    df_h1.index = df_h1.index.str.strip() 
    
    col_prev = df_h1.columns[0]
    col_curr = df_h1.columns[1]
    
    labels = ['Penduduk Usia Kerja', 'Angkatan Kerja', 'Bukan Angkatan Kerja', 'Bekerja', 'Pengangguran', 'Sekolah', 'Mengurus Rumah Tangga', 'Lainnya', 'Sektor Formal', 'Sektor Informal', 'Pernah Bekerja', 'Belum Pernah Bekerja']
    parents = ['', 'Penduduk Usia Kerja', 'Penduduk Usia Kerja', 'Angkatan Kerja', 'Angkatan Kerja', 'Bukan Angkatan Kerja', 'Bukan Angkatan Kerja', 'Bukan Angkatan Kerja', 'Bekerja', 'Bekerja', 'Pengangguran', 'Pengangguran']
    excel_rows = ['Penduduk 15 tahun ke atas', 'Angkatan Kerja', 'Bukan Angkatan kerja', 'Bekerja', 'Pengangguran', 'Sekolah', 'Mengurus Rumah Tangga', 'Lainnya', 'Formal', 'Informal', 'Pernah Bekerja', 'Tidak Pernah Bekerja']

    values = [df_h1.loc[r, col_curr] for r in excel_rows]
    values_prev = [df_h1.loc[r, col_prev] for r in excel_rows]
    
    # 1. PERBAIKAN TOOLTIP: Pembulatan Eksplisit dari sisi Python
    # Membulatkan nilai perubahan menjadi 2 desimal sejak awal untuk memastikan bersih
    perubahan = [round(((curr - prev) / prev) * 100, 2) for curr, prev in zip(values, values_prev)]
    
    # Kita ubah angka perubahan menjadi teks (string) format Indonesia 
    # (misal: "0.77" menjadi "+0,77") agar tooltip tidak bingung
    perubahan_str = []
    for p in perubahan:
        prefix = "+" if p > 0 else ""
        formatted_p = f"{prefix}{p:.2f}".replace('.', ',')
        perubahan_str.append(formatted_p)

    # Gabungkan data untuk tooltip (Volume Sebelumnya, Perubahan Angka Asli (untuk warna), Perubahan Teks (untuk Tooltip))
    customdata = list(zip(values_prev, perubahan, perubahan_str))

    # 2. PERBAIKAN LEGENDA
    min_pct = min(perubahan)
    max_pct = max(perubahan)
    
    # Agar angka tidak bertumpuk, kita buat ujung rentang warna lebih besar/lebih kecil
    # secara simetris, misalnya dari -10% hingga +10%. Ini akan mencegah penumpukan label.
    cmin_val = -10.0
    cmax_val = 10.0
    
    # Titik statis yang pasti rapi
    tick_vals = [cmin_val, -5, 0, 5, cmax_val]
    tick_texts = [f"{cmin_val:.0f}%", "-5%", "0%", "5%", f"{cmax_val:.0f}%"]

    fig = go.Figure(go.Icicle(
        labels=labels,
        parents=parents,
        values=values,
        customdata=customdata,
        branchvalues="total",
        tiling=dict(orientation='h'), 
        
        marker=dict(
            colors=perubahan, 
            colorscale=[[0, '#D55E00'], [0.5, '#F8FAFC'], [1, '#0072B2']], 
            # Menggunakan rentang tetap -10 ke 10 agar gradasi seimbang
            cmin=cmin_val,
            cmax=cmax_val,
            cmid=0,
            line=dict(color='#FFFFFF', width=3),
            showscale=True,
            colorbar=dict(
                title=dict(text="Perubahan Jumlah Penduduk (%)", font=dict(size=12, color="#64748B")),
                orientation="h",
                y=-0.15,
                thickness=12,
                len=0.8,
                tickvals=tick_vals,
                ticktext=tick_texts,
                outlinewidth=1,
                outlinecolor="#64748B"
            )
        ),
        
        pathbar=dict(
            visible=True,
            side='top',
            thickness=25,
            textfont=dict(size=13, family='Inter', color='#0F172A')
        ),

        # Perhatikan %{customdata[2]} yang mengambil nilai teks yang sudah diformat koma lokal
        hovertemplate=
            "<b>%{label}</b><br>" +
            "Volume Saat Ini, %{value:,.0f}<br>" +
            "Volume Sebelumnya, %{customdata[0]:,.0f}<br>" +
            "Perubahan, %{customdata[2]}%<br>" +
            "Proporsi Total, %{percentParent:.2%}<extra></extra>",
        textinfo="label+percent parent"
    ))
    
    fig.update_layout(
        margin=dict(t=30, l=0, r=0, b=60), 
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", size=12),
        separators=",.", # Format Indonesia
        hoverlabel=dict(
            bgcolor="#ffffff",
            font_size=10,
            font_family="Inter",
            font_color="black",
            bordercolor="#334155",
            align="left"
        )
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def prepare_treemap_data():
    # 1. Baca dan bersihkan data
    df_h2 = pd.read_excel('data.xlsx', sheet_name='Hirarki 2').iloc[:, :5]
    df_h2 = df_h2.dropna(subset=['Jumlah penduduk'])
    df_h2['Pendidikan Terakhir'] = df_h2['Pendidikan Terakhir'].astype(str).str.strip()
    
    # 2. Palet Warna Buta Warna (Okabe-Ito)
    colorblind_safe_palette = ['#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00']
    
    # Memetakan Ijazah ke warna spesifik
    edu_levels = df_h2['Pendidikan Terakhir'].unique()
    color_discrete_map = {edu: colorblind_safe_palette[i % len(colorblind_safe_palette)] for i, edu in enumerate(edu_levels)}
    color_discrete_map['(?)'] = '#E2E8F0' 
    
    # 3. Buat Treemap
    fig = px.treemap(
        df_h2, 
        path=[px.Constant("Pekerja & Penganggur"), 'Kegiatan', 'Kelompok Umur', 'Jenis Kelamin', 'Pendidikan Terakhir'], 
        values='Jumlah penduduk',
        color='Pendidikan Terakhir',
        color_discrete_map=color_discrete_map
    )
    
    # 4. Styling Gap, Tooltip, dan Teks Dalam Kotak
    fig.update_traces(
        marker=dict(line=dict(color='#F7F8FA', width=3)), 
        hovertemplate=
            "<b>%{label}</b><br>" +
            "Volume, %{value:,.0f} Jiwa<br>" +
            "Proporsi Induk, %{percentParent:.2%}<br>" +
            "Proporsi Total, %{percentRoot:.2%}<extra></extra>",
        # PERUBAHAN: Hanya tampilkan nama kategori dan persentase di dalam kotak
        textinfo="label+percent parent" 
    )
    
    # 5. TRIK LEGENDA: Menambahkan kotak kosong khusus untuk memancing legenda
    for edu, color in color_discrete_map.items():
        if edu != '(?)': # Kita abaikan warna abu-abu induk
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=14, color=color, symbol='square'),
                name=edu,
                showlegend=True
            ))

    # 6. Pembaruan Layout
    fig.update_layout(
        # Sisakan jarak lebih besar di bagian bawah (b=80) untuk tempat legenda
        margin=dict(t=30, l=0, r=0, b=80), 
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", size=12),
        separators=",.", 
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        hoverlabel=dict(
            bgcolor="#ffffff",
            font_size=10,
            font_family="Inter",
            font_color="black",
            bordercolor="#334155",
            align="left"
        ),
        # Menampilkan dan memposisikan legenda di tengah bawah
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.05,
            xanchor="center",
            x=0.5,
            title=dict(text="Ijazah Terakhir:", font=dict(color="#64748B")),
            font=dict(size=11)
        )
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def prepare_geo_data():
    # --- 1. Pra-pemrosesan Data Excel (Sesuai Logika map_generator.py Anda) ---
    df_geo = pd.read_excel('data.xlsx', sheet_name='Geografis')
    
    # Identifikasi baris Provinsi dan propagasi ke bawah
    df_geo['Is_Provinsi'] = df_geo['Prov Kab/Kota'] == df_geo['Prov Kab/Kota'].str.upper()
    df_geo['Nama Provinsi'] = np.where(df_geo['Is_Provinsi'], df_geo['Prov Kab/Kota'], np.nan)
    df_geo['Nama Provinsi'] = df_geo['Nama Provinsi'].ffill()
    
    # Buang agregat Provinsi dan Nasional untuk mendapatkan data Kabupaten murni
    df_clean = df_geo[~df_geo['Is_Provinsi']].copy()
    df_clean = df_clean[df_clean['Prov Kab/Kota'].str.upper() != 'INDONESIA']
    
    # Bersihkan nama kabupaten dari spasi kosong untuk pencocokan GeoJSON
    df_clean['Nama_peta_kab'] = df_clean['Nama_peta_kab'].astype(str).str.strip()

    # --- 2. Siapkan data JSON untuk dikirim ke Browser ---
    out_data = []
    for _, row in df_clean.iterrows():
        # Memastikan tidak mengirim data kosong
        if pd.isna(row['TPT 2025']) or pd.isna(row['TPAK 2025 L']):
            continue
            
        out_data.append({
            'kab_name': str(row['Prov Kab/Kota']),
            'geojson_id': row['Nama_peta_kab'], # Ini KUNCI untuk mencocokkan dengan GeoJSON Anda
            'tpt': row['TPT 2025'],
            'tpak_l': row['TPAK 2025 L'],
            'tpak_p': row['TPAK 2025 P']
        })
        
    return json.dumps(out_data)

def prepare_network_data():
    df_geo = pd.read_excel('data.xlsx', sheet_name='Geografis')
    
    # 1. Ambil data agregat Provinsi
    df_geo['Is_Provinsi'] = df_geo['Prov Kab/Kota'] == df_geo['Prov Kab/Kota'].str.upper()
    df_prov = df_geo[df_geo['Is_Provinsi'] & (df_geo['Prov Kab/Kota'] != 'INDONESIA')].copy()
    df_prov = df_prov.dropna(subset=['TPT 2025'])
    
    prov_names = df_prov['Prov Kab/Kota'].tolist()
    tpt_values = df_prov[['TPT 2025']].values
    
    # 2. Palet Warna Ramah Buta Warna (Biru = Rendah, Abu = Menengah, Oranye = Tinggi)
    # Ini menggantikan RdYlGn_r (Merah-Hijau) yang rentan
    cmap = mcolors.LinearSegmentedColormap.from_list("cb_safe", ["#0072B2", "#F8FAFC", "#D55E00"])
    min_tpt, max_tpt = tpt_values.min(), tpt_values.max()
    norm = mcolors.Normalize(vmin=min_tpt, vmax=max_tpt)

    def get_hex_color(val):
        return mcolors.to_hex(cmap(norm(val)))

    # 3. Hitung Matriks Jarak Euclidean (Selisih TPT)
    dist_matrix = squareform(pdist(tpt_values, metric='euclidean'))
    G = nx.Graph()
    
    # 4. Membangun Node (Titik Simpul)
    for i, name in enumerate(prov_names):
        tpt_val = tpt_values[i][0]
        # Mengubah teks menjadi Title Case agar lebih rapi (misal: "Jawa Barat")
        G.add_node(i, label=name.title(), tpt=tpt_val, color=get_hex_color(tpt_val))
        
    # 5. Membangun Edge (Garis Penghubung)
    THRESHOLD = 0.3
    for i in range(len(prov_names)):
        for j in range(i + 1, len(prov_names)):
            selisih = dist_matrix[i, j]
            if selisih <= THRESHOLD:
                bobot = round((THRESHOLD - selisih) * 10, 2)
                avg_tpt = (tpt_values[i][0] + tpt_values[j][0]) / 2
                
                G.add_edge(i, j, value=bobot, color=get_hex_color(avg_tpt), selisih=selisih)

    # 6. Menghitung Ukuran Node berdasarkan Degree Centrality
    centrality = nx.degree_centrality(G)
    
    # Menyusun format JSON spesifik untuk pustaka Vis.js di Front-End
    nodes_data = []
    for node_id in G.nodes():
        node = G.nodes[node_id]
        size = (centrality[node_id] * 40) + 12 # Ukuran dasar
        nodes_data.append({
            'id': node_id,
            'label': node['label'],
            'title': f"<div style='padding:5px; font-family:Inter;'><b>{node['label']}</b><br>TPT: {node['tpt']}%</div>",
            'size': size,
            'color': {
                'background': node['color'],
                'border': '#CBD5E1',
                'hover': {'background': node['color'], 'border': '#0F172A'}
            },
            'borderWidth': 1.5,
            'font': {'color': '#1E293B', 'size': 11, 'face': 'Inter'}
        })
        
    edges_data = []
    for u, v, data in G.edges(data=True):
        edges_data.append({
            'from': u,
            'to': v,
            'value': data['value'],
            'title': f"<div style='padding:5px; font-family:Inter;'>Kemiripan Kuat<br>Selisih TPT: {data['selisih']:.2f}%</div>",
            'color': {'color': data['color'], 'opacity': 0.5, 'highlight': '#0F172A'}
        })
        
    return json.dumps({'nodes': nodes_data, 'edges': edges_data})

def prepare_multivariate_data():
    df_multi = pd.read_excel('data.xlsx', sheet_name='Multivariate')
    features = ['TPT', 'TPAK', 'PDRB per Kapita', 'Persentase Penduduk Miskin', 
                'RLS', 'AHH', 'IPM', 'Gini Ratio', 'Kepadatan Penduduk', 'Laju pertumbuhan']
    
    # Bersihkan spasi kosong
    df_multi = df_multi.dropna(subset=features + ['Pulau'])
    df_multi['Pulau'] = df_multi['Pulau'].astype(str).str.strip()
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_multi[features])
    
    pca = PCA(n_components=2)
    components = pca.fit_transform(X_scaled)
    
    df_multi['PC1'] = components[:, 0]
    df_multi['PC2'] = components[:, 1]
    var_ratio = pca.explained_variance_ratio_ * 100
    
    # AGREGASI RADAR CHART: Menghitung rata-rata profil (Z-score) untuk masing-masing ke-6 Pulau
    df_scaled = pd.DataFrame(X_scaled, columns=features)
    df_scaled['Pulau'] = df_multi['Pulau'].values
    # Mengelompokkan data per pulau dan mengambil rata-ratanya
    radar_aggregated = df_scaled.groupby('Pulau').mean().to_dict('index')
    
    data_json = {
        'provinsi': df_multi['Provinsi'].tolist(),
        'pulau': df_multi['Pulau'].tolist(),
        'pc1': df_multi['PC1'].tolist(),
        'pc2': df_multi['PC2'].tolist(),
        'var_pc1': round(var_ratio[0], 2),
        'var_pc2': round(var_ratio[1], 2),
        'features': features,
        'radar_pulau': radar_aggregated, # Mengirim data agregat 6 pulau ke JS
        'raw_data': df_multi[features].to_dict('records')
    }

    data_json = {
        'provinsi': df_multi['Provinsi'].tolist(),
        'pulau': df_multi['Pulau'].tolist(),
        'pc1': df_multi['PC1'].tolist(),
        'pc2': df_multi['PC2'].tolist(),
        'var_pc1': round(var_ratio[0], 2),
        'var_pc2': round(var_ratio[1], 2),
        'features': features,
        'radar_pulau': radar_aggregated, 
        'radar_data': X_scaled.tolist(), 
        'raw_data': df_multi[features].to_dict('records')
    }
    
    return json.dumps(data_json)


def prepare_flow_data():
    df_flow = pd.read_excel('data.xlsx', sheet_name='Flow 2')
    df_flow = df_flow.rename(columns={'Nama Provinsi': 'Origin'})
    
    # "Unpivot" data dari bentuk matriks ke format tabel panjang (Origin -> Destination -> Volume)
    df_melt = df_flow.melt(id_vars=['Origin'], var_name='Destination', value_name='Volume')
    df_melt = df_melt.dropna(subset=['Volume'])
    df_melt['Origin'] = df_melt['Origin'].astype(str).str.strip()
    df_melt['Destination'] = df_melt['Destination'].astype(str).str.strip()
    
    # Hapus perpindahan ke provinsi itu sendiri dan yang bervolume 0
    df_melt = df_melt[df_melt['Origin'] != df_melt['Destination']]
    df_melt['Volume'] = pd.to_numeric(df_melt['Volume'], errors='coerce')
    df_melt = df_melt.dropna(subset=['Volume'])
    df_melt = df_melt[df_melt['Volume'] > 0]
    
    # Basis koordinat (Pusat Provinsi)
    prov_coords = {
        'ACEH': [4.6951, 96.7494], 'SUMATERA UTARA': [2.1154, 99.5451], 'SUMATERA BARAT': [-0.7399, 100.8000],
        'RIAU': [0.2933, 101.7068], 'JAMBI': [-1.6116, 103.6131], 'SUMATERA SELATAN': [-3.3194, 103.9144],
        'BENGKULU': [-3.5778, 102.3464], 'LAMPUNG': [-4.5586, 105.4068], 'KEPULAUAN BANGKA BELITUNG': [-2.7411, 106.4406],
        'KEP. BANGKA BELITUNG': [-2.7411, 106.4406], 'KEPULAUAN RIAU': [3.9456, 108.1429], 'DKI JAKARTA': [-6.2088, 106.8456], 
        'JAWA BARAT': [-6.9204, 107.6046], 'JAWA TENGAH': [-7.1509, 110.1403], 'DI YOGYAKARTA': [-7.7956, 110.3695], 
        'D I YOGYAKARTA': [-7.7956, 110.3695], 'JAWA TIMUR': [-7.5360, 112.2384], 'BANTEN': [-6.4058, 106.0640], 
        'BALI': [-8.4095, 115.1889], 'NUSA TENGGARA BARAT': [-8.6529, 117.3616], 'NUSA TENGGARA TIMUR': [-8.6225, 121.0794], 
        'KALIMANTAN BARAT': [-0.2788, 111.4753], 'KALIMANTAN TENGAH': [-1.6815, 113.3824], 'KALIMANTAN SELATAN': [-3.0926, 115.2838],
        'KALIMANTAN TIMUR': [0.5387, 116.4194], 'KALIMANTAN UTARA': [3.0731, 116.0414], 'SULAWESI UTARA': [0.6247, 123.9750], 
        'SULAWESI TENGAH': [-1.4300, 121.4456], 'SULAWESI SELATAN': [-3.6688, 119.9740], 'SULAWESI TENGGARA': [-4.1449, 122.1746],
        'GORONTALO': [0.6999, 122.4467], 'SULAWESI BARAT': [-2.8441, 119.2321], 'MALUKU': [-3.2385, 130.1453], 
        'MALUKU UTARA': [1.5709, 127.8088], 'PAPUA BARAT': [-1.3361, 133.1747], 'PAPUA': [-4.2699, 138.0804],
        'PAPUA SELATAN': [-7.4285, 139.7348], 'PAPUA TENGAH': [-3.9922, 136.2736], 'PAPUA PEGUNUNGAN': [-4.2250, 139.3090], 
        'PAPUA BARAT DAYA': [-0.8872, 131.7877]
    }

    flows = []
    for _, row in df_melt.iterrows():
        o = row['Origin']
        d = row['Destination']
        if o in prov_coords and d in prov_coords:
            flows.append({
                'origin': o, 'dest': d, 'vol': int(row['Volume']),
                'o_lat': prov_coords[o][0], 'o_lon': prov_coords[o][1],
                'd_lat': prov_coords[d][0], 'd_lon': prov_coords[d][1]
            })
            
    # Ekstrak daftar provinsi unik untuk menu Dropdown
    unique_provs = sorted(list(set([f['origin'] for f in flows] + [f['dest'] for f in flows])))
    
    data_json = {'flows': flows, 'provinces': unique_provs}
    return json.dumps(data_json)


def prepare_chord_data():
    df = pd.read_excel('data.xlsx', sheet_name='Flow 1')
    
    # Ekstrak matriks angka saja (buang kolom nama 'Sektor')
    mat = df.drop(columns=['Sektor']).fillna(0).values
    
    # KUNCI: Kosongkan nilai diagonal utama agar grafik hanya berfokus pada PERPINDAHAN
    # np.fill_diagonal(mat, 0)
    matrix = mat.tolist()
    
    # Mendefinisikan 17 Sektor Lapangan Usaha sesuai standar BPS
    sektor_names = [
        "Pertanian", "Pertambangan", "Industri Pengolahan", "Pengadaan Listrik", 
        "Pengadaan Air & Limbah", "Konstruksi", "Perdagangan", "Transportasi", 
        "Akomodasi & Mamin", "Infokom", "Jasa Keuangan", "Real Estat", 
        "Jasa Perusahaan", "Adm. Pemerintahan", "Jasa Pendidikan", 
        "Kesehatan", "Jasa Lainnya"
    ]
    
    return json.dumps({
        "matrix": matrix,
        "names": sektor_names
    })


@app.route('/')
def index():
    # 1. Buat data hierarki (Icicle dan Treemap)
    icicle_json = prepare_icicle_data()
    treemap_json = prepare_treemap_data()
    geo_json = prepare_geo_data()
    network_json = prepare_network_data()
    multi_json = prepare_multivariate_data()
    flow_json=prepare_flow_data()
    chord_json=prepare_chord_data() 
    return render_template('index.html', 
                           icicle_json=icicle_json,
                           treemap_json=treemap_json,
                           geo_json=geo_json,
                           network_json=network_json,
                           multi_json=multi_json,
                           flow_json=flow_json,
                           chord_json=chord_json
                        )
    
if __name__ == '__main__':
    app.run(debug=True)