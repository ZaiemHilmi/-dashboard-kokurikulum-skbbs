"""
Dashboard Kokurikulum SKBBS 2026
Memuatkan data daripada semua kelas Tahun 4, 5 dan 6
(sheets T4 kelas, T5 kelas, T6 Ikut kelas)
Jumlah: ~609 murid
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import io
import warnings
import datetime
from fpdf import FPDF
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Kokurikulum SKBBS 2026",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #0f172a 0%, #1a2744 50%, #0f172a 100%);
    padding: 1.8rem 2.5rem; border-radius: 16px; margin-bottom: 1.5rem;
    border: 1px solid #1e40af44; text-align: center;
}
.main-header h1 { font-family:'Rajdhani',sans-serif; color:#38bdf8; font-size:2rem; font-weight:700; margin:0; letter-spacing:2px; }
.main-header p  { color:#94a3b8; margin:0.3rem 0 0 0; font-size:0.9rem; }

.kpi-card {
    background: linear-gradient(135deg,#0f172a,#1e293b);
    border: 1px solid #1e40af55; border-radius: 12px;
    padding: 1.1rem 1rem; text-align: center;
    box-shadow: 0 4px 18px rgba(0,0,0,0.35); height: 100%;
}
.kpi-num   { font-family:'Rajdhani',sans-serif; font-size:2.2rem; font-weight:700; color:#38bdf8; line-height:1; }
.kpi-label { color:#94a3b8; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; margin-top:0.3rem; }
.kpi-sub   { color:#64748b; font-size:0.75rem; margin-top:0.2rem; }

.section-title {
    font-family:'Rajdhani',sans-serif; color:#38bdf8; font-size:1.15rem; font-weight:600;
    letter-spacing:1px; border-bottom:1px solid #1e40af44; padding-bottom:0.4rem; margin-bottom:1rem;
}
.alert-card { border-radius:10px; padding:0.75rem 1rem; margin-bottom:0.5rem; font-size:0.87rem; font-weight:500; }
.alert-red    { background:#450a0a; border-left:4px solid #ef4444; color:#fca5a5; }
.alert-orange { background:#431407; border-left:4px solid #f97316; color:#fdba74; }
.alert-yellow { background:#422006; border-left:4px solid #eab308; color:#fde047; }
.alert-green  { background:#052e16; border-left:4px solid #22c55e; color:#86efac; }
.alert-blue   { background:#0c1a40; border-left:4px solid #3b82f6; color:#93c5fd; }
.tahun-badge { display:inline-block; border-radius:20px; padding:3px 14px; font-size:0.8rem; font-weight:600; margin:3px; }
.t4 { background:#1e3a5f; color:#38bdf8; border:1px solid #1e40af; }
.t5 { background:#1a3322; color:#34d399; border:1px solid #166534; }
.t6 { background:#3b1f5e; color:#c084fc; border:1px solid #7c3aed; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
SHEET_CONFIG = [("T4 kelas", "4"), ("T5 kelas", "5"), ("T6 Ikut kelas", "6")]
COLUMNS = ["BIL","NAMA MURID","JANTINA","KAUM","KELAS","UB","PERSATUAN","SUKAN","1M1S","RUMAH SUKAN"]
GENDER_MAP = {
    "L":"Lelaki","LELAKI":"Lelaki","MALE":"Lelaki","M":"Lelaki",
    "P":"Perempuan","PEREMPUAN":"Perempuan","FEMALE":"Perempuan","F":"Perempuan",
}
COLORS_GENDER = {"Lelaki":"#38bdf8","Perempuan":"#f472b6"}
COLORS_TAHUN  = {"Tahun 4":"#38bdf8","Tahun 5":"#34d399","Tahun 6":"#c084fc"}
COLORWAY = ["#38bdf8","#f472b6","#34d399","#fbbf24","#a78bfa","#fb7185","#60a5fa","#4ade80"]

def dark(fig, height=None):
    upd = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a",
        font_color="#94a3b8", font_family="Inter", colorway=COLORWAY,
        xaxis=dict(gridcolor="#1e293b", linecolor="#334155"),
        yaxis=dict(gridcolor="#1e293b", linecolor="#334155"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font_color="#94a3b8"),
        margin=dict(t=45, b=40, l=40, r=20),
    )
    if height: upd["height"] = height
    fig.update_layout(**upd)
    return fig

def normalise_kelas(k, tahun):
    s = str(k).strip().upper()
    if s in ("NAN","","NONE"): return None
    try: float(s); return None
    except ValueError: pass
    return s if s.startswith(f"{tahun} ") else f"{tahun} {s}"

# ─────────────────────────────────────────────
# DATA LOADER
# ─────────────────────────────────────────────
@st.cache_data
def load_all(file_bytes=None):
    frames = []
    for sheet_name, tahun in SHEET_CONFIG:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), engine="xlrd",
                               sheet_name=sheet_name, header=5)
            if df.shape[1] < 8: continue
            rename = {df.columns[i]: COLUMNS[i] for i in range(min(len(COLUMNS), df.shape[1]))}
            df = df.rename(columns=rename)
            df["BIL"] = pd.to_numeric(df["BIL"], errors="coerce")
            df = df[df["BIL"].notna()].copy()
            df["TAHUN"] = tahun
            df["TAHUN_LABEL"] = "Tahun " + tahun
            df["SHEET"] = sheet_name
            df["KELAS"] = df["KELAS"].apply(lambda k: normalise_kelas(k, tahun))
            df["JANTINA"] = (df["JANTINA"].astype(str).str.strip().str.upper()
                             .map(lambda x: GENDER_MAP.get(x, None)))
            df = df[df["JANTINA"].notna()]
            df = df[df["NAMA MURID"].astype(str).str.strip().str.len() > 2]
            for col in ["UB","PERSATUAN","SUKAN","KAUM","RUMAH SUKAN"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip().str.upper()
                    df[col] = df[col].replace({"NAN":None,"":None,"NONE":None})
            frames.append(df)
        except Exception as e:
            st.warning(f"Sheet '{sheet_name}' tidak dapat dibaca: {e}")
    if not frames: return None
    return pd.concat(frames, ignore_index=True)

# ─────────────────────────────────────────────
# SMART ALERTS
# ─────────────────────────────────────────────
def generate_alerts(df):
    alerts = []
    for col_unit, label in [("UB","Unit Beruniform"),("PERSATUAN","Persatuan"),("SUKAN","Sukan")]:
        if col_unit not in df.columns or df[col_unit].dropna().empty: continue
        counts = df[col_unit].value_counts()
        avg = counts.mean()
        for unit, cnt in counts.items():
            if cnt <= max(1, avg * 0.4):
                alerts.append(("orange", f"🟠 {label} <b>'{unit}'</b> — hanya {cnt} ahli (purata: {avg:.0f})"))
        if "JANTINA" in df.columns:
            g = df.groupby([col_unit,"JANTINA"]).size().unstack(fill_value=0)
            for unit in g.index:
                row = g.loc[unit]; total = row.sum()
                if total == 0: continue
                dom = row.max()
                if dom / total >= 0.72:
                    dom_g = row.idxmax(); pct = int(dom/total*100)
                    alerts.append(("red", f"🔴 {label} <b>'{unit}'</b> — {pct}% {dom_g} (ketidakseimbangan jantina)"))
    for col_unit, label in [("UB","Unit Beruniform"),("PERSATUAN","Persatuan"),("SUKAN","Sukan")]:
        if col_unit in df.columns and not df[col_unit].dropna().empty:
            top = df[col_unit].value_counts().idxmax()
            cnt = df[col_unit].value_counts().max()
            alerts.append(("green", f"🟢 {label} terpopular: <b>'{top}'</b> ({cnt} ahli)"))
    return alerts


# ─────────────────────────────────────────────
# PDF GENERATOR
# ─────────────────────────────────────────────
def generate_pdf(df, tajuk_laporan, nama_sekolah="SK BANDAR BARU SINTOK"):
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    # Header
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 35, "F")
    pdf.set_text_color(56, 189, 248)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_y(8)
    pdf.cell(0, 8, nama_sekolah, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, tajuk_laporan, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Dijana pada: {datetime.datetime.now().strftime('%d/%m/%Y  %H:%M')}", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(0, 0, 0)
    pdf.set_y(42)

    # Statistik ringkasan
    total = len(df)
    lelaki = (df["JANTINA"] == "Lelaki").sum()
    perempuan = (df["JANTINA"] == "Perempuan").sum()

    pdf.set_fill_color(230, 241, 251)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "RINGKASAN STATISTIK", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.ln(1)

    stats = [
        ("Jumlah Murid", str(total)),
        ("Lelaki", f"{lelaki} ({int(lelaki/total*100) if total else 0}%)"),
        ("Perempuan", f"{perempuan} ({int(perempuan/total*100) if total else 0}%)"),
        ("Bilangan Kelas", str(df["KELAS"].nunique())),
        ("Unit Beruniform", str(df["UB"].nunique()) + " jenis"),
        ("Persatuan/Kelab", str(df["PERSATUAN"].nunique()) + " jenis"),
        ("Sukan", str(df["SUKAN"].nunique()) + " jenis"),
    ]
    for label, val in stats:
        pdf.set_fill_color(248, 250, 252)
        pdf.cell(70, 6, "  " + label, border="B", fill=True)
        pdf.cell(0, 6, val, border="B", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # UB breakdown
    pdf.set_fill_color(230, 241, 251)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "PENYERTAAN UNIT BERUNIFORM", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("Helvetica", "B", 9)
    pdf.ln(1)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(70, 6, "Unit Beruniform", border=1, fill=True)
    pdf.cell(30, 6, "Jumlah", border=1, fill=True)
    pdf.cell(35, 6, "Lelaki", border=1, fill=True)
    pdf.cell(35, 6, "Perempuan", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for ub, grp in df.groupby("UB"):
        if pd.isna(ub): continue
        l = (grp["JANTINA"] == "Lelaki").sum()
        p = (grp["JANTINA"] == "Perempuan").sum()
        pdf.cell(70, 6, "  " + str(ub), border=1)
        pdf.cell(30, 6, str(len(grp)), border=1)
        pdf.cell(35, 6, str(l), border=1)
        pdf.cell(35, 6, str(p), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Kelas breakdown
    pdf.set_fill_color(230, 241, 251)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "BILANGAN MURID PER KELAS", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("Helvetica", "B", 9)
    pdf.ln(1)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(60, 6, "Kelas", border=1, fill=True)
    pdf.cell(30, 6, "Jumlah", border=1, fill=True)
    pdf.cell(35, 6, "Lelaki", border=1, fill=True)
    pdf.cell(35, 6, "Perempuan", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for kelas, grp in df.groupby("KELAS"):
        if pd.isna(kelas): continue
        l = (grp["JANTINA"] == "Lelaki").sum()
        p = (grp["JANTINA"] == "Perempuan").sum()
        pdf.cell(60, 6, "  " + str(kelas), border=1)
        pdf.cell(30, 6, str(len(grp)), border=1)
        pdf.cell(35, 6, str(l), border=1)
        pdf.cell(35, 6, str(p), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Senarai penuh murid
    pdf.add_page()
    pdf.set_fill_color(230, 241, 251)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "SENARAI PENUH MURID", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("Helvetica", "B", 8)
    pdf.ln(1)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(8,  5, "Bil", border=1, fill=True)
    pdf.cell(65, 5, "Nama Murid", border=1, fill=True)
    pdf.cell(18, 5, "Jantina", border=1, fill=True)
    pdf.cell(22, 5, "Kelas", border=1, fill=True)
    pdf.cell(28, 5, "UB", border=1, fill=True)
    pdf.cell(30, 5, "Persatuan", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7)
    for i, row in df.reset_index(drop=True).iterrows():
        if pdf.get_y() > 270:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(8,  5, "Bil", border=1, fill=True)
            pdf.cell(65, 5, "Nama Murid", border=1, fill=True)
            pdf.cell(18, 5, "Jantina", border=1, fill=True)
            pdf.cell(22, 5, "Kelas", border=1, fill=True)
            pdf.cell(28, 5, "UB", border=1, fill=True)
            pdf.cell(30, 5, "Persatuan", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 7)
        fill = i % 2 == 0
        pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
        nama = str(row.get("NAMA MURID", ""))[:35]
        pdf.cell(8,  5, str(i+1), border=1, fill=fill)
        pdf.cell(65, 5, nama, border=1, fill=fill)
        pdf.cell(18, 5, str(row.get("JANTINA", "")), border=1, fill=fill)
        pdf.cell(22, 5, str(row.get("KELAS", "")), border=1, fill=fill)
        pdf.cell(28, 5, str(row.get("UB", ""))[:12], border=1, fill=fill)
        pdf.cell(30, 5, str(row.get("PERSATUAN", ""))[:14], border=1, fill=fill, new_x="LMARGIN", new_y="NEXT")

    # Footer setiap page
    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, f"Dashboard Kokurikulum SKBBS 2026  |  Halaman {pdf.page_no()}  |  Sulit", align="C")

    return bytes(pdf.output())


# ─────────────────────────────────────────────
# SIDEBAR — UPLOAD
# ─────────────────────────────────────────────
# Simpan file bytes dalam session_state supaya kekal bila filter berubah
with st.sidebar:
    st.markdown("### 📂 Muat Naik Fail Excel")
    uploaded = st.file_uploader(
        "Seret & lepas fail di sini",
        type=["xls","xlsx"],
        help="Muat naik fail Kokurikulum_murid_SKBBS_2026.xls"
    )
    st.markdown("---")

# Bila ada fail baru diupload, simpan bytes dalam session_state
if uploaded is not None:
    st.session_state["file_bytes"] = uploaded.read()

# Guna bytes dari session_state (kekal walaupun filter berubah)
if "file_bytes" not in st.session_state:
    st.markdown("""
    <div style="text-align:center; padding: 4rem 2rem;">
        <div style="font-size:3rem; margin-bottom:1rem;">📂</div>
        <h2 style="font-family:'Rajdhani',sans-serif; color:#38bdf8; margin-bottom:0.5rem;">
            Muat Naik Fail Excel
        </h2>
        <p style="color:#94a3b8; font-size:0.95rem; margin-bottom:1.5rem;">
            Sila muat naik fail <b>Kokurikulum_murid_SKBBS_2026.xls</b><br>
            menggunakan panel di sebelah kiri.
        </p>
        <div style="background:#0f172a; border:1px dashed #1e40af; border-radius:12px; padding:1.2rem 2rem; display:inline-block; color:#64748b; font-size:0.85rem;">
            📌 Sidebar kiri → "Muat Naik Fail Excel" → pilih fail .xls
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

with st.spinner("⏳ Memuatkan data semua kelas..."):
    df_master = load_all(file_bytes=st.session_state["file_bytes"])

if df_master is None or df_master.empty:
    st.error("❌ Gagal memuatkan data. Pastikan fail yang betul dimuat naik.")
    st.stop()

# ─────────────────────────────────────────────
# PRE-CLEAN: buang data kotor sekali je
# ─────────────────────────────────────────────
df_clean = df_master.copy()
df_clean = df_clean[df_clean["KELAS"].notna() & ~df_clean["KELAS"].astype(str).str.contains("UNKNOWN", na=True)]
df_clean = df_clean[df_clean["JANTINA"].isin(["Lelaki","Perempuan"])]
df_clean = df_clean.reset_index(drop=True)

# SIDEBAR — FILTERS (CASCADING — bergantung antara satu sama lain)
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Penapis")

    # Tahun (dari semua data bersih)
    tahuns = sorted(df_clean["TAHUN_LABEL"].dropna().unique())
    sel_tahun = st.multiselect("📅 Tahun", tahuns, default=tahuns)

    # Kelas (hanya tunjuk kelas yang ada dalam Tahun terpilih)
    _df_t = df_clean[df_clean["TAHUN_LABEL"].isin(sel_tahun)] if sel_tahun else df_clean
    klases = sorted(_df_t["KELAS"].dropna().unique())
    sel_kelas = st.multiselect("🏫 Kelas", klases, default=klases)

    # Jantina
    sel_gender = st.multiselect("👤 Jantina", ["Lelaki","Perempuan"], default=["Lelaki","Perempuan"])

    # UB, Persatuan, Sukan (bergantung pada Tahun+Kelas terpilih)
    _df_k = _df_t[_df_t["KELAS"].isin(sel_kelas)] if sel_kelas else _df_t
    ubs   = sorted(_df_k["UB"].dropna().unique())
    sel_ub = st.multiselect("🎖️ Unit Beruniform", ubs, default=ubs)
    perss = sorted(_df_k["PERSATUAN"].dropna().unique())
    sel_p = st.multiselect("📚 Persatuan", perss, default=perss)
    sukans = sorted(_df_k["SUKAN"].dropna().unique())
    sel_s = st.multiselect("⚽ Sukan", sukans, default=sukans)

    st.markdown("---")
    st.markdown("### 💾 Muat Turun")
    buf = io.StringIO()
    df_clean.to_csv(buf, index=False)
    st.download_button("⬇️ Data Penuh (CSV)", data=buf.getvalue(),
                       file_name="kokurikulum_skbbs_2026_semua.csv", mime="text/csv")
    st.markdown("---")
    st.markdown("<div style='color:#475569;font-size:0.72rem;text-align:center'>📊 SKBBS Kokurikulum Dashboard<br>Versi 2.0 · Tahun 4–6 · 2026</div>", unsafe_allow_html=True)

# APPLY ALL FILTERS
# ─────────────────────────────────────────────
df = df_clean.copy()
if sel_tahun:  df = df[df["TAHUN_LABEL"].isin(sel_tahun)]
if sel_kelas:  df = df[df["KELAS"].isin(sel_kelas)]
if sel_gender: df = df[df["JANTINA"].isin(sel_gender)]
if sel_ub:     df = df[df["UB"].isin(sel_ub)]
if sel_p:      df = df[df["PERSATUAN"].isin(sel_p)]
if sel_s:      df = df[df["SUKAN"].isin(sel_s)]
df = df.reset_index(drop=True)

total     = len(df)
lelaki    = (df["JANTINA"] == "Lelaki").sum()
perempuan = (df["JANTINA"] == "Perempuan").sum()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
total_db = len(df_clean)
st.markdown(f"""
<div class="main-header">
    <h1>🏫 DASHBOARD KOKURIKULUM SKBBS 2026</h1>
    <p>Sekolah Kebangsaan Bandar Baru Sintok &nbsp;·&nbsp;
    <span class="tahun-badge t4">Tahun 4</span>
    <span class="tahun-badge t5">Tahun 5</span>
    <span class="tahun-badge t6">Tahun 6</span>
    &nbsp;·&nbsp; {total_db} murid dalam pangkalan data</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊  Gambaran Keseluruhan",
    "🏫  Analisis Kelas",
    "🎖️  Unit Beruniform",
    "📚  Persatuan & Sukan",
    "🧠  Analitik & Amaran",
    "🔍  Carian Murid",
    "📄  Laporan PDF",
])

# ══════════════════════════════════
# TAB 1 — GAMBARAN KESELURUHAN
# ══════════════════════════════════
with tab1:
    n_kelas = df["KELAS"].nunique()
    n_ub    = df["UB"].nunique()
    n_p     = df["PERSATUAN"].nunique()
    n_s     = df["SUKAN"].nunique()
    l_pct   = int(lelaki/total*100) if total else 0
    p_pct   = 100 - l_pct

    k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
    for col_obj, num, label, sub in [
        (k1, str(total),     "Jumlah Murid",    "rekod ditapis"),
        (k2, str(lelaki),    "Lelaki",           f"{l_pct}%"),
        (k3, str(perempuan), "Perempuan",        f"{p_pct}%"),
        (k4, str(n_kelas),   "Kelas",            "dalam data"),
        (k5, str(n_ub),      "Unit Beruniform",  "jenis"),
        (k6, str(n_p),       "Persatuan/Kelab",  "jenis"),
        (k7, str(n_s),       "Sukan",            "jenis"),
    ]:
        with col_obj:
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-num">{num}</div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-sub">{sub}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-title">Taburan Jantina (Semua Tahun)</div>', unsafe_allow_html=True)
        gdf = df["JANTINA"].value_counts().reset_index()
        gdf.columns = ["Jantina","Bil"]
        fig = px.pie(gdf, names="Jantina", values="Bil", hole=0.42,
                     color="Jantina", color_discrete_map=COLORS_GENDER)
        fig.update_traces(textinfo="percent+label+value", textfont_size=12)
        dark(fig, 320)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.markdown('<div class="section-title">Bilangan Murid Mengikut Tahun & Jantina</div>', unsafe_allow_html=True)
        t_df = df.groupby(["TAHUN_LABEL","JANTINA"]).size().reset_index(name="Bilangan")
        fig2 = px.bar(t_df, x="TAHUN_LABEL", y="Bilangan", color="JANTINA",
                      barmode="group", text="Bilangan",
                      color_discrete_map=COLORS_GENDER,
                      labels={"TAHUN_LABEL":"Tahun"})
        fig2.update_traces(textposition="outside")
        dark(fig2, 320)
        st.plotly_chart(fig2, width="stretch")

    st.markdown('<div class="section-title">Penyertaan Unit Beruniform — Mengikut Tahun</div>', unsafe_allow_html=True)
    ub_t = df.groupby(["UB","TAHUN_LABEL"]).size().reset_index(name="Bilangan")
    fig3 = px.bar(ub_t, x="UB", y="Bilangan", color="TAHUN_LABEL",
                  barmode="stack", text_auto=True,
                  color_discrete_map=COLORS_TAHUN,
                  labels={"UB":"Unit Beruniform","TAHUN_LABEL":"Tahun"})
    dark(fig3, 360)
    st.plotly_chart(fig3, width="stretch")

    st.markdown('<div class="section-title">Senarai Murid</div>', unsafe_allow_html=True)
    search = st.text_input("🔎 Cari nama murid", placeholder="Taip nama...")
    disp = df[["NAMA MURID","JANTINA","KELAS","TAHUN_LABEL","UB","PERSATUAN","SUKAN"]].copy()
    if search:
        disp = disp[disp["NAMA MURID"].str.upper().str.contains(search.upper(), na=False)]
    st.dataframe(disp.reset_index(drop=True), width="stretch", height=360)
    buf2 = io.StringIO(); disp.to_csv(buf2, index=False)
    st.download_button("⬇️ Muat turun senarai ini (CSV)", data=buf2.getvalue(),
                       file_name="senarai_murid_ditapis.csv", mime="text/csv")

# ══════════════════════════════════
# TAB 2 — ANALISIS KELAS
# ══════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">Bilangan Murid Per Kelas</div>', unsafe_allow_html=True)
    kelas_df    = df.groupby(["KELAS","TAHUN_LABEL","JANTINA"]).size().reset_index(name="Bilangan")
    kelas_order = df.groupby("KELAS").size().sort_values(ascending=False).index.tolist()
    fig_k = px.bar(kelas_df, x="KELAS", y="Bilangan", color="JANTINA",
                   barmode="stack", text_auto=True,
                   color_discrete_map=COLORS_GENDER,
                   category_orders={"KELAS": kelas_order},
                   labels={"KELAS":"Kelas"})
    fig_k.update_layout(xaxis_tickangle=-30)
    dark(fig_k, 430)
    st.plotly_chart(fig_k, width="stretch")

    for tahun_label, color, badge_cls in [
        ("Tahun 4","#38bdf8","t4"),
        ("Tahun 5","#34d399","t5"),
        ("Tahun 6","#c084fc","t6"),
    ]:
        sub = df[df["TAHUN_LABEL"] == tahun_label]
        if sub.empty: continue
        st.markdown(f'<div class="section-title"><span class="tahun-badge {badge_cls}">{tahun_label}</span> — Ringkasan Per Kelas</div>', unsafe_allow_html=True)
        kelas_list = sorted(sub["KELAS"].dropna().unique())
        cols_k = st.columns(len(kelas_list)) if kelas_list else [st.container()]
        for i, kelas in enumerate(kelas_list):
            ks = sub[sub["KELAS"] == kelas]
            l_c = (ks["JANTINA"] == "Lelaki").sum()
            p_c = (ks["JANTINA"] == "Perempuan").sum()
            with cols_k[i]:
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-num" style="font-size:1.6rem;color:{color}">{len(ks)}</div>
                    <div class="kpi-label">{kelas}</div>
                    <div class="kpi-sub">👦 {l_c} &nbsp;|&nbsp; 👧 {p_c}</div>
                </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Matriks: Kelas × Unit Beruniform</div>', unsafe_allow_html=True)
    cross = pd.crosstab(df["KELAS"], df["UB"])
    fig_heat = px.imshow(cross, text_auto=True, color_continuous_scale="Blues", aspect="auto")
    dark(fig_heat, 420)
    st.plotly_chart(fig_heat, width="stretch")

# ══════════════════════════════════
# TAB 3 — UNIT BERUNIFORM
# ══════════════════════════════════
with tab3:
    st.markdown('<div class="section-title">Jumlah Ahli per Unit Beruniform</div>', unsafe_allow_html=True)
    ub_total = df["UB"].value_counts().reset_index(); ub_total.columns = ["UB","Bilangan"]
    c1, c2 = st.columns([2,1])
    with c1:
        fig_ub = px.bar(ub_total, x="UB", y="Bilangan", text="Bilangan",
                        color="Bilangan", color_continuous_scale="Blues")
        fig_ub.update_traces(textposition="outside"); fig_ub.update_coloraxes(showscale=False)
        dark(fig_ub, 350); st.plotly_chart(fig_ub, width="stretch")
    with c2:
        ub_g = df.groupby(["UB","JANTINA"]).size().unstack(fill_value=0)
        ub_g["Jumlah"] = ub_g.sum(axis=1)
        st.dataframe(ub_g.reset_index(), width="stretch", height=280)

    ub_tahun = df.groupby(["UB","TAHUN_LABEL"]).size().reset_index(name="Bilangan")
    fig_ubt = px.bar(ub_tahun, x="UB", y="Bilangan", color="TAHUN_LABEL",
                     barmode="group", text="Bilangan",
                     color_discrete_map=COLORS_TAHUN, title="Unit Beruniform Mengikut Tahun",
                     labels={"TAHUN_LABEL":"Tahun"})
    fig_ubt.update_traces(textposition="outside"); dark(fig_ubt, 380)
    st.plotly_chart(fig_ubt, width="stretch")

    ub_gender = df.groupby(["UB","JANTINA"]).size().reset_index(name="Bilangan")
    fig_ubg = px.bar(ub_gender, x="UB", y="Bilangan", color="JANTINA",
                     barmode="stack", text="Bilangan",
                     color_discrete_map=COLORS_GENDER, title="Komposisi Jantina per UB")
    dark(fig_ubg, 360); st.plotly_chart(fig_ubg, width="stretch")

    st.markdown('<div class="section-title">Peratusan Jantina per Unit Beruniform</div>', unsafe_allow_html=True)
    pct = df.groupby(["UB","JANTINA"]).size().unstack(fill_value=0)
    total_col = pct.sum(axis=1)
    for col in pct.columns:
        pct[f"% {col}"] = (pct[col] / total_col * 100).round(1).astype(str) + "%"
    st.dataframe(pct.reset_index(), width="stretch")

# ══════════════════════════════════
# TAB 4 — PERSATUAN & SUKAN
# ══════════════════════════════════
with tab4:
    c_p, c_s = st.columns(2)
    with c_p:
        st.markdown('<div class="section-title">📚 Persatuan / Kelab</div>', unsafe_allow_html=True)
        p_cnt = df["PERSATUAN"].value_counts().reset_index(); p_cnt.columns = ["Persatuan","Bilangan"]
        fig_p = px.bar(p_cnt, y="Persatuan", x="Bilangan", orientation="h",
                       text="Bilangan", color="Bilangan", color_continuous_scale="Teal")
        fig_p.update_traces(textposition="outside")
        fig_p.update_layout(yaxis=dict(categoryorder="total ascending"))
        fig_p.update_coloraxes(showscale=False); dark(fig_p, 480)
        st.plotly_chart(fig_p, width="stretch")

    with c_s:
        st.markdown('<div class="section-title">⚽ Sukan</div>', unsafe_allow_html=True)
        s_cnt = df["SUKAN"].value_counts().reset_index(); s_cnt.columns = ["Sukan","Bilangan"]
        fig_s = px.bar(s_cnt, y="Sukan", x="Bilangan", orientation="h",
                       text="Bilangan", color="Bilangan", color_continuous_scale="Oranges")
        fig_s.update_traces(textposition="outside")
        fig_s.update_layout(yaxis=dict(categoryorder="total ascending"))
        fig_s.update_coloraxes(showscale=False); dark(fig_s, 480)
        st.plotly_chart(fig_s, width="stretch")

    c_pg, c_sg = st.columns(2)
    with c_pg:
        p_g = df.groupby(["PERSATUAN","JANTINA"]).size().reset_index(name="Bil")
        fig_pg = px.bar(p_g, y="PERSATUAN", x="Bil", color="JANTINA", orientation="h",
                        barmode="stack", color_discrete_map=COLORS_GENDER,
                        title="Jantina per Persatuan")
        fig_pg.update_layout(yaxis=dict(categoryorder="total ascending"))
        dark(fig_pg, 480); st.plotly_chart(fig_pg, width="stretch")

    with c_sg:
        s_g = df.groupby(["SUKAN","JANTINA"]).size().reset_index(name="Bil")
        fig_sg = px.bar(s_g, y="SUKAN", x="Bil", color="JANTINA", orientation="h",
                        barmode="stack", color_discrete_map=COLORS_GENDER,
                        title="Jantina per Sukan")
        fig_sg.update_layout(yaxis=dict(categoryorder="total ascending"))
        dark(fig_sg, 480); st.plotly_chart(fig_sg, width="stretch")

    st.markdown('<div class="section-title">Persatuan Mengikut Tahun</div>', unsafe_allow_html=True)
    p_tahun = df.groupby(["PERSATUAN","TAHUN_LABEL"]).size().reset_index(name="Bilangan")
    fig_pt = px.bar(p_tahun, x="PERSATUAN", y="Bilangan", color="TAHUN_LABEL",
                    barmode="stack", text_auto=True,
                    color_discrete_map=COLORS_TAHUN, labels={"TAHUN_LABEL":"Tahun"})
    fig_pt.update_layout(xaxis_tickangle=-35); dark(fig_pt, 380)
    st.plotly_chart(fig_pt, width="stretch")

    st.markdown('<div class="section-title">🔥 Heatmap: Unit Beruniform × Persatuan</div>', unsafe_allow_html=True)
    cross2 = pd.crosstab(df["UB"], df["PERSATUAN"])
    fig_h = px.imshow(cross2, text_auto=True, color_continuous_scale="Blues", aspect="auto")
    dark(fig_h, 400); st.plotly_chart(fig_h, width="stretch")

# ══════════════════════════════════
# TAB 5 — ANALITIK & AMARAN
# ══════════════════════════════════
with tab5:
    st.markdown('<div class="section-title">🚨 Smart Alerts</div>', unsafe_allow_html=True)
    alerts = generate_alerts(df)
    css_map = {"red":"alert-red","orange":"alert-orange","yellow":"alert-yellow",
               "green":"alert-green","blue":"alert-blue"}
    if not alerts:
        st.success("✅ Tiada isu dikesan.")
    else:
        for sev, msg in alerts:
            cls = css_map.get(sev,"alert-blue")
            st.markdown(f'<div class="alert-card {cls}">{msg}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">🌐 Hierarki Penyertaan (Sunburst)</div>', unsafe_allow_html=True)
    sun = df[["TAHUN_LABEL","UB","JANTINA"]].dropna().copy(); sun["count"] = 1
    fig_sun = px.sunburst(sun, path=["TAHUN_LABEL","UB","JANTINA"], values="count",
                          color="TAHUN_LABEL", color_discrete_map=COLORS_TAHUN,
                          title="Hierarki: Tahun → Unit Beruniform → Jantina")
    dark(fig_sun, 500); fig_sun.update_traces(textinfo="label+percent entry")
    st.plotly_chart(fig_sun, width="stretch")

    c_stat1, c_stat2 = st.columns(2)
    with c_stat1:
        st.markdown("**📈 Status Unit Beruniform**")
        ub_v = df["UB"].value_counts(); avg_ub = ub_v.mean()
        st.dataframe(pd.DataFrame({
            "Unit": ub_v.index, "Bilangan": ub_v.values,
            "Status": ["🔴 Bawah" if v < avg_ub*0.7 else "🟡 Sederhana" if v < avg_ub else "🟢 Baik"
                       for v in ub_v.values]
        }), width="stretch", hide_index=True)

    with c_stat2:
        st.markdown("**⚽ Status Sukan**")
        s_v = df["SUKAN"].value_counts(); avg_s = s_v.mean()
        st.dataframe(pd.DataFrame({
            "Sukan": s_v.index, "Bilangan": s_v.values,
            "Status": ["🔴 Bawah" if v < avg_s*0.7 else "🟡 Sederhana" if v < avg_s else "🟢 Baik"
                       for v in s_v.values]
        }), width="stretch", hide_index=True)

    st.markdown('<div class="section-title">📋 Rumusan Eksekutif</div>', unsafe_allow_html=True)
    t4_c = (df["TAHUN"] == "4").sum()
    t5_c = (df["TAHUN"] == "5").sum()
    t6_c = (df["TAHUN"] == "6").sum()
    top_ub = df["UB"].value_counts().idxmax() if not df.empty else "-"
    top_p  = df["PERSATUAN"].value_counts().idxmax() if not df.empty else "-"
    top_s  = df["SUKAN"].value_counts().idxmax() if not df.empty else "-"
    st.markdown(f"""
    <div style="background:#0f172a;border:1px solid #1e40af44;border-radius:12px;padding:1.4rem 1.8rem;line-height:2.2;font-size:0.92rem;">
    📌 <b>Jumlah murid (ditapis):</b> <span style="color:#38bdf8">{total} orang</span>
    &nbsp;|&nbsp; <span style="color:#38bdf8">T4: {t4_c}</span>
    &nbsp;|&nbsp; <span style="color:#34d399">T5: {t5_c}</span>
    &nbsp;|&nbsp; <span style="color:#c084fc">T6: {t6_c}</span><br>
    👥 <b>Jantina:</b> <span style="color:#38bdf8">{l_pct}% Lelaki ({lelaki})</span>
    &nbsp;·&nbsp; <span style="color:#f472b6">{p_pct}% Perempuan ({perempuan})</span><br>
    🎖️ <b>UB paling ramai:</b> <span style="color:#fbbf24">{top_ub}</span><br>
    📚 <b>Persatuan paling popular:</b> <span style="color:#34d399">{top_p}</span><br>
    ⚽ <b>Sukan paling ramai peserta:</b> <span style="color:#a78bfa">{top_s}</span>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════
# TAB 6 — CARIAN MURID INDIVIDU
# ══════════════════════════════════
with tab6:
    st.markdown('<div class="section-title">🔍 Carian Murid Individu</div>', unsafe_allow_html=True)

    col_cari, col_kosong = st.columns([2, 1])
    with col_cari:
        carian = st.text_input(
            "Taip nama murid",
            placeholder="Contoh: Ahmad, Nur Aisyah...",
            key="carian_murid"
        )

    if not carian:
        st.markdown("""
        <div style="text-align:center;padding:3rem 1rem;background:#0f172a;border-radius:12px;border:1px dashed #1e40af;">
            <div style="font-size:2.5rem;margin-bottom:0.8rem;">🔍</div>
            <p style="color:#38bdf8;font-size:1.1rem;font-weight:600;margin:0 0 0.4rem;">Cari Murid</p>
            <p style="color:#64748b;font-size:0.85rem;margin:0;">Taip nama murid di atas untuk lihat profil lengkap</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        hasil = df_clean[df_clean["NAMA MURID"].str.upper().str.contains(carian.upper(), na=False)]

        if hasil.empty:
            st.warning(f"❌ Tiada murid dijumpai dengan nama mengandungi **'{carian}'**")
        else:
            st.success(f"✅ Dijumpai **{len(hasil)}** murid")
            st.markdown("<br>", unsafe_allow_html=True)

            for _, row in hasil.iterrows():
                nama    = str(row.get("NAMA MURID", "-"))
                jantina = str(row.get("JANTINA", "-"))
                kelas   = str(row.get("KELAS", "-"))
                tahun   = str(row.get("TAHUN_LABEL", "-"))
                ub      = str(row.get("UB", "-")) if pd.notna(row.get("UB")) else "-"
                persatuan = str(row.get("PERSATUAN", "-")) if pd.notna(row.get("PERSATUAN")) else "-"
                sukan   = str(row.get("SUKAN", "-")) if pd.notna(row.get("SUKAN")) else "-"
                kaum    = str(row.get("KAUM", "-")) if pd.notna(row.get("KAUM")) else "-"
                icon    = "👦" if jantina == "Lelaki" else "👧"
                warna_tahun = "#38bdf8" if "4" in tahun else "#34d399" if "5" in tahun else "#c084fc"

                initials = "".join([w[0] for w in nama.split()[:2]]) if nama != "-" else "?"

                st.markdown(f"""
                <div style="background:#0f172a;border:1px solid #1e40af44;border-radius:14px;padding:1.3rem 1.5rem;margin-bottom:1rem;">
                    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;border-bottom:1px solid #1e293b;padding-bottom:1rem;">
                        <div style="width:52px;height:52px;border-radius:50%;background:#1e3a5f;display:flex;align-items:center;justify-content:center;font-family:'Rajdhani',sans-serif;font-size:1.2rem;font-weight:700;color:#38bdf8;flex-shrink:0;">
                            {initials}
                        </div>
                        <div>
                            <div style="font-family:'Rajdhani',sans-serif;font-size:1.15rem;font-weight:700;color:#f1f5f9;letter-spacing:0.5px;">{icon} {nama}</div>
                            <div style="font-size:0.8rem;color:#64748b;margin-top:2px;">{jantina} &nbsp;·&nbsp; <span style="color:{warna_tahun}">{tahun}</span> &nbsp;·&nbsp; Kelas {kelas}</div>
                        </div>
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.8rem;">
                        <div style="background:#1e293b;border-radius:8px;padding:0.7rem 1rem;">
                            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;">🎖️ Unit Beruniform</div>
                            <div style="font-size:0.95rem;color:#38bdf8;font-weight:600;">{ub}</div>
                        </div>
                        <div style="background:#1e293b;border-radius:8px;padding:0.7rem 1rem;">
                            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;">📚 Persatuan</div>
                            <div style="font-size:0.95rem;color:#34d399;font-weight:600;">{persatuan}</div>
                        </div>
                        <div style="background:#1e293b;border-radius:8px;padding:0.7rem 1rem;">
                            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;">⚽ Sukan</div>
                            <div style="font-size:0.95rem;color:#fbbf24;font-weight:600;">{sukan}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Export hasil carian
            st.markdown("---")
            buf_cari = io.StringIO()
            hasil[["NAMA MURID","JANTINA","KELAS","TAHUN_LABEL","UB","PERSATUAN","SUKAN"]].to_csv(buf_cari, index=False)
            st.download_button(
                f"⬇️ Export hasil carian ({len(hasil)} murid) sebagai CSV",
                data=buf_cari.getvalue(),
                file_name=f"carian_{carian.replace(' ','_')}.csv",
                mime="text/csv"
            )

# ══════════════════════════════════
# TAB 7 — LAPORAN PDF
# ══════════════════════════════════
with tab7:
    st.markdown('<div class="section-title">📄 Jana Laporan PDF Rasmi</div>', unsafe_allow_html=True)

    col_opt1, col_opt2 = st.columns(2)

    with col_opt1:
        st.markdown("**⚙️ Tetapan Laporan**")
        tajuk_custom = st.text_input(
            "Tajuk laporan",
            value="LAPORAN PENYERTAAN KOKURIKULUM 2026",
            key="tajuk_pdf"
        )
        nama_sekolah_pdf = st.text_input(
            "Nama sekolah",
            value="SEKOLAH KEBANGSAAN BANDAR BARU SINTOK",
            key="nama_skolah_pdf"
        )

    with col_opt2:
        st.markdown("**📋 Data yang akan dimasukkan dalam PDF**")
        st.markdown(f"""
        <div style="background:#0f172a;border:1px solid #1e40af44;border-radius:10px;padding:1rem 1.2rem;font-size:0.88rem;line-height:2;">
        ✅ Ringkasan statistik (jumlah murid, jantina)<br>
        ✅ Pecahan Unit Beruniform<br>
        ✅ Bilangan murid per kelas<br>
        ✅ Senarai penuh murid<br>
        📌 Berdasarkan <b style="color:#38bdf8">{total} murid</b> dalam penapis semasa
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Preview ringkas
    st.markdown("**👁️ Pratonton Data**")
    prev_cols = st.columns(4)
    for col_obj, num, label, color in [
        (prev_cols[0], str(total), "Jumlah Murid", "#38bdf8"),
        (prev_cols[1], str(lelaki), "Lelaki", "#38bdf8"),
        (prev_cols[2], str(perempuan), "Perempuan", "#f472b6"),
        (prev_cols[3], str(df["KELAS"].nunique()), "Kelas", "#34d399"),
    ]:
        with col_obj:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-num" style="color:{color}">{num}</div>
                <div class="kpi-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_jana, col_info = st.columns([1, 2])
    with col_jana:
        jana_pdf = st.button("🖨️ Jana PDF Sekarang", type="primary", use_container_width=True)

    with col_info:
        # Show filter info
        filter_aktif = []
        if len(sel_tahun) < 3: filter_aktif.append(f"Tahun: {', '.join(sel_tahun)}")
        if len(sel_kelas) < len(df_clean["KELAS"].dropna().unique()): filter_aktif.append(f"{len(sel_kelas)} kelas dipilih")
        if len(sel_gender) < 2: filter_aktif.append(f"Jantina: {', '.join(sel_gender)}")
        if filter_aktif:
            st.info(f"📌 Penapis aktif: {' | '.join(filter_aktif)}")
        else:
            st.info("📌 Tiada penapis — laporan akan merangkumi semua murid")

    if jana_pdf:
        if df.empty:
            st.error("❌ Tiada data untuk dijana. Semak penapis anda.")
        else:
            with st.spinner("⏳ Menjana laporan PDF... sila tunggu..."):
                try:
                    pdf_bytes = generate_pdf(df, tajuk_custom, nama_sekolah_pdf)
                    tarikh_fail = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                    nama_fail   = f"Laporan_Kokurikulum_SKBBS_{tarikh_fail}.pdf"

                    st.success(f"✅ PDF berjaya dijana! ({len(pdf_bytes)//1024} KB)")
                    st.download_button(
                        label="⬇️ Muat turun Laporan PDF",
                        data=pdf_bytes,
                        file_name=nama_fail,
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                    )
                    st.markdown(f"""
                    <div style="background:#052e16;border:1px solid #22c55e44;border-radius:10px;padding:0.8rem 1.2rem;margin-top:0.8rem;font-size:0.85rem;color:#86efac;">
                    📄 <b>{nama_fail}</b> dah sedia untuk dimuat turun.<br>
                    Fail PDF mengandungi {total} rekod murid dengan {len(df["KELAS"].dropna().unique())} kelas.
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"❌ Ralat menjana PDF: {e}")

