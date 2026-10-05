# Web Story Dinamika Ketenagakerjaan Indonesia

Sebuah narasi visual berbasis data yang membedah komposisi, perubahan, dan kemiripan struktural angkatan kerja di Indonesia. Web story ini dirancang untuk memberikan visualisasi yang interaktif dalam memahami dinamika pasar kerja Indonesia melalui analisis geospasial, jaringan relasi, reduksi dimensi, hingga aliran migrasi secara interaktif.

Proyek ini dibangun untuk menyajikan narasi data yang kompleks menjadi eksplorasi visual yang intuitif, mendukung  interaktivitas pengguna, sehingga dapat mendorong analisis yang lebih mendalam.

## Fitur Visualisasi Utama (7 Bab Eksplorasi)

1. **Struktur Demografi (Icicle/Treemap)**
   Mengurai anatomi angkatan kerja berdasarkan status pekerjaan, kelompok usia, gender, hingga tingkat pendidikan menggunakan visualisasi hierarkis multi-level.
2. **Peta Choropleth Pengangguran (TPT)**
   Peta interaktif yang memvisualisasikan Tingkat Pengangguran Terbuka (TPT) di seluruh provinsi dengan warna sekuensial.
3. **Peta Simbol Partisipasi Kerja (TPAK)**
   Menyoroti anomali dan dominasi partisipasi angkatan kerja berdasarkan gender di area rural maupun urban.
4. **Jaring Kekerabatan Pengangguran (Network Graph)**
   Menerapkan visualisasi jaringan untuk menghubungkan provinsi-provinsi yang memiliki karakteristik tingkat pengangguran serupa ke dalam simpul interaktif.
5. **Analisis Multivariat (PCA, Radar & Parallel Coordinates)**
   Eksplorasi dimensi tinggi menggunakan *Principal Component Analysis* (PCA). Mendukung fitur **Brushing & Linking**: Seleksi titik provinsi di diagram Scatter PCA akan secara langsung meredupkan garis di *Parallel Coordinates* dan membentuk agregasi rata-rata poligon baru di *Radar Chart*.
6. **Jejak Eksodus Geografis (Flow Map)**
   Memetakan arus migrasi tenaga kerja antar provinsi menggunakan garis lengkung (*Bezier Curves*) yang membedakan arus masuk dan arus keluar.
7. **Transisi Karier Sektoral (Chord Diagram)**
   Diagram pita (*Directed Chord*) yang dirender menggunakan **D3.js** untuk melacak perpindahan/banting setir pekerja lintas 17 sektor lapangan usaha.

## Tumpukan Teknologi (Tech Stack)

**Backend / Data Processing:**
* [Python 3.10](https://www.python.org/)
* [Flask 3.0](https://flask.palletsprojects.com/) (Web Framework)
* [Pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/) (Manipulasi Data)
* [Scikit-Learn](https://scikit-learn.org/) (Standardisasi & Komputasi PCA)
* [SciPy](https://scipy.org/) & [NetworkX](https://networkx.org/) (Kalkulasi jarak matriks & Centrality)


**Frontend / Data Visualization:**
* [Plotly.js](https://plotly.com/javascript/) (Render Chart, Peta Mapbox, PCA, Parallel Coordinates)
* [D3.js (v7)](https://d3js.org/) (Custom Directed Chord Diagram)
* [Vis.js Network](https://visjs.org/) (Fisika Jaring Kekerabatan)
* Vanilla JavaScript, HTML5, & CSS3


## Struktur Direktori

```text
├── app.py                  # Skrip utama backend (Flask application & rute JSON)
├── data.xlsx               # Dataset utama
├── requirements.txt        # Daftar dependensi pustaka 
├── static/                 
│   └── css/
│       └── style.css       # Styling
└── templates/
    └── index.html          # Halaman utama Web Story yang memuat seluruh visualisasi JS
```
## Panduan Instalasi Lokal
Jika Anda ingin menjalankan proyek ini di komputer lokal Anda, ikuti langkah-langkah berikut:

1. Clone Repositori

```Bash
cd NAMA_REPOSITORI
git clone https://github.com/Ridhopurwanto/Web-Visualisasi-Data.git
```

2. Buat Virtual Environment (Sangat Disarankan)

```Bash
python -m venv venv
```

## Aktivasi di Windows:
```
venv\Scripts\activate
```
## Aktivasi di Mac/Linux:
```
source venv/bin/activate
```

3. Instal Dependensi

```Bash
pip install -r requirements.txt
```

4. Jalankan Aplikasi
```Bash
python app.py
```
Buka browser dan akses http://127.0.0.1:5000/.

## Link web story
https://ridho29.pythonanywhere.com/
