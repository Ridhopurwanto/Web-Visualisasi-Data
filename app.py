from flask import Flask, render_template
import pandas as pd
import plotly.express as px
import plotly.utils
import json
from map_generator import generate_map, generate_network
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import plotly.graph_objects as go
import pydeck as pdk

app = Flask(__name__)

def prepare_hierarki_data():
    # --- Siapkan Data Icicle (Sheet 1) ---
    df_h1 = pd.read_excel('data.xlsx', sheet_name='Hirarki 1')
    df_h1.columns = ['Kategori', 'Ags_2025', 'Feb_2026']
    
    parents_map = {
        'Penduduk 15 tahun ke atas': '',
        'Angkatan Kerja': 'Penduduk 15 tahun ke atas',
        'Bukan Angkatan kerja': 'Penduduk 15 tahun ke atas',
        'Bekerja': 'Angkatan Kerja',
        'Pengangguran': 'Angkatan Kerja',
        'Sekolah': 'Bukan Angkatan kerja',
        'Mengurus Rumah Tangga': 'Bukan Angkatan kerja',
        'Lainnya': 'Bukan Angkatan kerja',
        'Informal': 'Bekerja',
        'Formal': 'Bekerja',
        'Pernah Bekerja': 'Pengangguran',
        'Tidak Pernah Bekerja': 'Pengangguran'
    }
    
    df_icicle = df_h1[df_h1['Kategori'].isin(parents_map.keys())].copy()
    df_icicle['Parent'] = df_icicle['Kategori'].map(parents_map)
    df_icicle['Perubahan (%)'] = ((df_icicle['Feb_2026'] - df_icicle['Ags_2025']) / df_icicle['Ags_2025']) * 100

    # Buat Plotly Figure Icicle
    fig_icicle = px.icicle(
        df_icicle, names='Kategori', parents='Parent', values='Feb_2026',
        color='Perubahan (%)', color_continuous_scale='RdBu_r', color_continuous_midpoint=0,
        branchvalues='total'
    )
    fig_icicle.update_traces(root_color="lightgrey", tiling=dict(orientation='v'))
    
    fig_icicle.update_layout(margin=dict(t=40, l=10, r=10, b=10), paper_bgcolor='rgba(0,0,0,0)')

    # --- Siapkan Data Treemap (Sheet 2) ---
    df_h2 = pd.read_excel('data.xlsx', sheet_name='Hirarki 2')
    df_h2 = df_h2.loc[:, ~df_h2.columns.str.contains('^Unnamed')]
    
    pendidikan_map = {
        'Sekolah Dasar ke Bawah': 1, 'Sekolah Menegah Pertama': 2,
        'Sekolah Menegah Atas': 3, 'Sekolah Menegah Kejuruan': 3, 
        'Diploma I/II/III': 4, 'Diploma IV,S1,S2,S3': 5
    }
    df_h2['Nilai Pendidikan'] = df_h2['Pendidikan Terakhir'].map(pendidikan_map)
    df_h2 = df_h2.dropna(subset=['Jumlah penduduk'])

    # Buat Plotly Figure Treemap
    fig_treemap = px.treemap(
        df_h2, path=['Kegiatan', 'Kelompok Umur', 'Jenis Kelamin', 'Pendidikan Terakhir'],
        values='Jumlah penduduk', color='Nilai Pendidikan', color_continuous_scale='Blues'
    )
    fig_treemap.update_layout(coloraxis_showscale=False, margin=dict(t=40, l=10, r=10, b=10), paper_bgcolor='rgba(0,0,0,0)')

    return fig_icicle, fig_treemap

def prepare_multivariate_data():
    df_multi = pd.read_excel('data.xlsx', sheet_name='Multivariate')
    
    features = ['TPT', 'TPAK', 'PDRB per Kapita', 'Persentase Penduduk Miskin', 
                'RLS', 'AHH', 'Melek Huruf', 'Gini Ratio', 'Kepadatan Penduduk', 'Laju pertumbuhan']
    
    # Pastikan membuang baris yang kosong pada fitur atau Pulau
    df_multi = df_multi.dropna(subset=features + ['Pulau'])
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_multi[features])
    
    pca = PCA(n_components=2)
    components = pca.fit_transform(X_scaled)
    
    df_multi['PC1'] = components[:, 0]
    df_multi['PC2'] = components[:, 1]
    var_ratio = pca.explained_variance_ratio_ * 100
    
    # Tambahkan 'pulau' ke dalam output JSON
    data_json = {
        'provinsi': df_multi['Provinsi'].tolist(),
        'pulau': df_multi['Pulau'].tolist(), # <--- TAMBAHAN BARU
        'pc1': df_multi['PC1'].tolist(),
        'pc2': df_multi['PC2'].tolist(),
        'var_pc1': round(var_ratio[0], 2),
        'var_pc2': round(var_ratio[1], 2),
        'features': features,
        'radar_data': scaler.fit_transform(df_multi[features]).tolist(), 
        'raw_data': df_multi[features].to_dict('records')
    }
    
    return data_json


def generate_flow_map():
    # ====================================================
    # A. FLOW 2: MIGRASI PENDUDUK (PYDECK 3D ARC LAYER)
    # ====================================================
    df_f2_raw = pd.read_excel('data.xlsx', sheet_name='Flow 2')
    df_f2 = df_f2_raw.melt(id_vars=['Nama Provinsi'], var_name='Tujuan', value_name='Jumlah')
    df_f2 = df_f2.rename(columns={'Nama Provinsi': 'Asal'})
    
    df_f2 = df_f2.dropna(subset=['Jumlah'])
    df_f2 = df_f2[df_f2['Jumlah'] > 0]
    df_f2 = df_f2[df_f2['Asal'] != df_f2['Tujuan']]
    
    # Filter nilai ekstrem (sesuaikan threshold ini jika perlu)
    df_f2 = df_f2[df_f2['Jumlah'] > 5000]

    prov_coords = {
        'ACEH': [4.6951, 96.7494], 'SUMATERA UTARA': [2.1154, 99.5451], 'SUMATERA BARAT': [-0.7399, 100.8000],
        'RIAU': [0.2933, 101.7068], 'JAMBI': [-1.6116, 103.6131], 'SUMATERA SELATAN': [-3.3194, 103.9144],
        'BENGKULU': [-3.5778, 102.3464], 'LAMPUNG': [-4.5586, 105.4068], 'KEP. BANGKA BELITUNG': [-2.7411, 106.4406],
        'KEPULAUAN RIAU': [3.9456, 108.1429], 'DKI JAKARTA': [-6.2088, 106.8456], 'JAWA BARAT': [-6.9204, 107.6046],
        'JAWA TENGAH': [-7.1509, 110.1403], 'DI YOGYAKARTA': [-7.7956, 110.3695], 'JAWA TIMUR': [-7.5360, 112.2384],
        'BANTEN': [-6.4058, 106.0640], 'BALI': [-8.4095, 115.1889], 'NUSA TENGGARA BARAT': [-8.6529, 117.3616],
        'NUSA TENGGARA TIMUR': [-8.6225, 121.0794], 'KALIMANTAN BARAT': [-0.2788, 111.4753],
        'KALIMANTAN TENGAH': [-1.6815, 113.3824], 'KALIMANTAN SELATAN': [-3.0926, 115.2838],
        'KALIMANTAN TIMUR': [0.5387, 116.4194], 'KALIMANTAN UTARA': [3.0731, 116.0414],
        'SULAWESI UTARA': [0.6247, 123.9750], 'SULAWESI TENGAH': [-1.4300, 121.4456],
        'SULAWESI SELATAN': [-3.6688, 119.9740], 'SULAWESI TENGGARA': [-4.1449, 122.1746],
        'GORONTALO': [0.6999, 122.4467], 'SULAWESI BARAT': [-2.8441, 119.2321],
        'MALUKU': [-3.2385, 130.1453], 'MALUKU UTARA': [1.5709, 127.8088],
        'PAPUA BARAT': [-1.3361, 133.1747], 'PAPUA': [-4.2699, 138.0804],
        'PAPUA SELATAN': [-7.4285, 139.7348], 'PAPUA TENGAH': [-3.9922, 136.2736],
        'PAPUA PEGUNUNGAN': [-4.2250, 139.3090], 'PAPUA BARAT DAYA': [-0.8872, 131.7877]
    }

    # Memetakan koordinat ke dataframe
    df_f2['lat_asal'] = df_f2['Asal'].apply(lambda x: prov_coords.get(x, [0,0])[0])
    df_f2['lon_asal'] = df_f2['Asal'].apply(lambda x: prov_coords.get(x, [0,0])[1])
    df_f2['lat_tujuan'] = df_f2['Tujuan'].apply(lambda x: prov_coords.get(x, [0,0])[0])
    df_f2['lon_tujuan'] = df_f2['Tujuan'].apply(lambda x: prov_coords.get(x, [0,0])[1])
    
    # Hapus baris yang koordinatnya tidak ditemukan
    df_f2 = df_f2[(df_f2['lat_asal'] != 0) & (df_f2['lat_tujuan'] != 0)]

    # Normalisasi ketebalan garis (1 hingga 15)
    max_jumlah = df_f2['Jumlah'].max()
    df_f2['width'] = (df_f2['Jumlah'] / max_jumlah) * 15 + 1

    # Membuat Layer Busur (Arc) 3D
    arc_layer = pdk.Layer(
        "ArcLayer",
        data=df_f2,
        get_source_position=["lon_asal", "lat_asal"],
        get_target_position=["lon_tujuan", "lat_tujuan"],
        get_width="width",
        get_source_color=[46, 204, 113, 200], # Hijau transparan (Asal)
        get_target_color=[231, 76, 60, 200],  # Merah transparan (Tujuan)
        pickable=True,
        auto_highlight=True
    )

    # Kamera 3D miring (pitch 45) agar lengkungan busur terlihat
    view_state = pdk.ViewState(latitude=-2.5, longitude=118.0, zoom=4, pitch=45)

    # Render peta menggunakan tema Carto Light (mirip Esri Light Canvas)
    r = pdk.Deck(
        layers=[arc_layer], 
        initial_view_state=view_state, 
        map_style='light', 
        tooltip={"text": "{Asal} ➔ {Tujuan}\nJumlah Migran: {Jumlah} Jiwa"}
    )
    
    # Simpan sebagai HTML
    r.to_html("templates/flow_map_3d.html")


def prepare_sankey_data():
    # ====================================================
    # B. FLOW 1: PERPINDAHAN LAP. USAHA (SANKEY DIAGRAM)
    # ====================================================
    # (Letakkan seluruh kode Flow 1 / Sankey Anda yang sudah benar di sini)
    df_f1_raw = pd.read_excel('data.xlsx', sheet_name='Flow 1')
    df_f1 = df_f1_raw.melt(id_vars=['Sektor'], var_name='Sektor Tujuan', value_name='Jumlah')
    df_f1 = df_f1.rename(columns={'Sektor': 'Sektor Asal'})
    df_f1['Jumlah'] = df_f1['Jumlah'].astype(str).str.replace(',', '.')
    df_f1['Jumlah'] = pd.to_numeric(df_f1['Jumlah'], errors='coerce').fillna(0)
    df_f1 = df_f1[df_f1['Jumlah'] > 0.5]
    df_f1['Sektor Asal'] = df_f1['Sektor Asal'].astype(str) + '(Asal)'
    df_f1['Sektor Tujuan'] = df_f1['Sektor Tujuan'].astype(str) + '(Tujuan)'
    
    all_nodes = list(pd.unique(df_f1[['Sektor Asal', 'Sektor Tujuan']].values.ravel('K')))
    node_mapping = {node: i for i, node in enumerate(all_nodes)}
    
    source_indices = df_f1['Sektor Asal'].map(node_mapping).tolist()
    target_indices = df_f1['Sektor Tujuan'].map(node_mapping).tolist()
    values = df_f1['Jumlah'].tolist()
    node_colors = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#34495e', '#e67e22'] * 10
    
    fig_sankey = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=all_nodes, color=node_colors[:len(all_nodes)]),
        link=dict(source=source_indices, target=target_indices, value=values, color="rgba(189, 195, 199, 0.5)")
    )])
    fig_sankey.update_layout(title_text="Transisi Lapangan Usaha (Sankey Diagram)", font_size=11, margin=dict(t=40, l=10, r=10, b=10))

    return fig_sankey

@app.route('/')
def index():
    # 1. Buat data hierarki (Icicle dan Treemap)
    fig_icicle, fig_treemap = prepare_hierarki_data()
    icicle_json = json.dumps(fig_icicle, cls=plotly.utils.PlotlyJSONEncoder)
    treemap_json = json.dumps(fig_treemap, cls=plotly.utils.PlotlyJSONEncoder)
    
    # 2. Hasilkan peta geospasial terbaru
    # PASTIKAN mengubah "batas_kabkota.shp" dengan nama file SHP asli Anda
    generate_map('data.xlsx', 'peta_kab_kota/peta_kab_kota.shp')
    generate_network('data.xlsx') 

    # Panggil fungsi multivariate
    multi_data = prepare_multivariate_data()
    multi_json = json.dumps(multi_data)

    # 1. Generate peta 3D (disimpan sbg file HTML)
    generate_flow_map()
    
    # 2. Ambil data Sankey JSON
    fig_sankey = prepare_sankey_data()
    sankey_json = json.dumps(fig_sankey, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template('index.html', 
                           icicle_json=icicle_json, 
                           treemap_json=treemap_json,
                           multi_json=multi_json,     # Lempar ke HTML
                           sankey_json=sankey_json)   # Lempar ke HTML
    

# Route baru untuk memuat file HTML peta Folium (disematkan sebagai Iframe)
@app.route('/peta')
def peta():
    return render_template('peta_indo.html')

@app.route('/network')
def network_graph():
    return render_template('network_indo.html')

@app.route('/flowmap')
def flowmap():
    return render_template('flow_map_3d.html')

if __name__ == '__main__':
    app.run(debug=True)