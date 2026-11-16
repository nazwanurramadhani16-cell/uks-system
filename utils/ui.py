"""Tampilan bersama untuk seluruh halaman UKS (CSS, sidebar, komponen kartu)."""
import base64
import calendar
import html
import re
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

# ------------------------------------------------------------------ PALET
INK, MUTED, LINE = "#262B3D", "#5D6B6B", "#E6E8F5"
PURPLE, PINK, BLUE, GREEN, TEAL = "#7C66D6", "#F4A6AE", "#6FA8DC", "#4FB894", "#8FBDBE"
COLORWAY = [PURPLE, PINK, BLUE, GREEN, TEAL, "#B9A6F0"]

# tone -> (latar lembut, teks, warna solid)
TONES = {
    "purple": ("#E6E0FA", "#5E48B8", PURPLE),
    "pink": ("#FDE9E9", "#B5415A", PINK),
    "blue": ("#DDEBF7", "#2F6FA8", BLUE),
    "green": ("#DDF2EA", "#23785F", GREEN),
    "teal": ("#E3EFEF", "#3E5757", TEAL),
}
STATUS_TONE = {
    "Menunggu": "pink", "Dilayani": "blue", "Dirujuk": "purple", "Selesai": "green",
    "Dibuat": "pink", "Diterima": "blue", "Ditangani": "purple",
}
ROLE_LABEL = {"mahasiswa": "Mahasiswa", "petugas": "Petugas UKS",
              "admin": "Admin", "mitra": "Mitra faskes"}
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,500,1,0&display=swap');
:root{--f:'Plus Jakarta Sans',system-ui,-apple-system,'Segoe UI',sans-serif;--ink:#262B3D;--muted:#5D6B6B;--line:#E6E8F5;--canvas:#F5F6FF;
--p:#7C66D6;--pd:#5E48B8;--ps:#E6E0FA;--k:#F4A6AE;--ks:#FDE9E9;--kd:#B5415A;--b:#6FA8DC;--bs:#DDEBF7;--bd:#2F6FA8;--g:#4FB894;--gs:#DDF2EA;--gd:#23785F;--t:#8FBDBE;--ts:#E3EFEF}
.stApp{background:radial-gradient(900px 500px at 100% 0%,rgba(247,203,202,.45),transparent 60%),radial-gradient(800px 500px at 0% 100%,rgba(189,215,216,.5),transparent 60%),#ECEEFB}
.stApp,.stApp :is(p,div,label,li,a,h1,h2,h3,h4,h5,h6,button,input,textarea,td,th,small){font-family:var(--f)}
.stApp{color:var(--ink)}
[data-testid="stHeader"]{background:transparent}
[data-testid="stToolbar"]{right:1rem}
.block-container{max-width:1320px;padding:2rem 2.2rem 4rem}
.narrow .block-container{max-width:900px}
h1,h2,h3{letter-spacing:-.01em;color:var(--ink)}
/* sidebar */
[data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--line);border-radius:0 28px 28px 0}
[data-testid="stSidebarContent"]{padding:1.4rem 1rem 1rem}
.brand{display:flex;align-items:center;gap:.8rem;margin:0 .3rem 1.4rem}
.brand .logo{width:46px;height:46px;border-radius:15px;background:linear-gradient(135deg,#8E78E8,#6A55C9);display:grid;place-items:center;color:#fff;box-shadow:0 8px 18px rgba(124,102,214,.35)}
.brand b{display:block;font-size:1.05rem;font-weight:800}
.brand small{color:var(--muted);font-size:.78rem}
.brandlogo{background:#fff;border:1px solid var(--line);border-radius:20px;padding:.85rem 1rem;margin:0 .1rem .55rem;display:flex;justify-content:center;box-shadow:0 6px 18px rgba(124,102,214,.09)}
.brandlogo img{width:100%;max-width:200px;height:auto;display:block}
.brandcap{text-align:center;color:var(--muted);font-size:.68rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase;margin:0 0 1.4rem}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]{border-radius:14px;padding:.62rem .85rem;color:var(--muted);font-weight:600;border-left:3px solid transparent;margin-bottom:.15rem}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover{background:var(--canvas);color:var(--ink)}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"]{background:var(--ps);color:var(--pd);border-left-color:var(--p)}
.me{display:flex;align-items:center;gap:.7rem;background:var(--canvas);border-radius:18px;padding:.7rem .8rem;margin:1.2rem 0 .6rem}
.me b{display:block;font-size:.9rem;line-height:1.2}.me small{color:var(--muted);font-size:.76rem}
.nosb [data-testid="stSidebar"],.nosb [data-testid="stSidebarCollapsedControl"],.nosb [data-testid="stExpandSidebarButton"]{display:none}
/* material icon + avatar */
.ms{font-family:'Material Symbols Rounded';font-weight:500;font-style:normal;font-size:24px;line-height:1;display:inline-block;font-variation-settings:'FILL' 1,'wght' 500;-webkit-font-feature-settings:'liga';font-feature-settings:'liga';vertical-align:middle}
.av{width:40px;height:40px;border-radius:50%;flex:none;display:grid;place-items:center;font-weight:800;font-size:.85rem;color:#fff;background:linear-gradient(135deg,#8E78E8,#F4A6AE)}
.av.lg{width:56px;height:56px;font-size:1.1rem}
/* header */
.top{display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;margin-bottom:1.4rem}
.top h1{font-size:1.9rem;font-weight:800;margin:0;padding:0;line-height:1.15}
.top p{margin:.3rem 0 0;color:var(--muted);font-size:.95rem;max-width:60ch}
.pill{display:inline-flex;align-items:center;gap:.5rem;background:#fff;border-radius:999px;padding:.45rem .9rem .45rem .5rem;font-weight:600;font-size:.88rem;box-shadow:0 2px 10px rgba(124,102,214,.08)}
.pill.date{padding:.55rem 1rem;color:var(--muted)}
.pill .av{width:32px;height:32px;font-size:.75rem}
/* section title */
.sec{display:flex;justify-content:space-between;align-items:baseline;margin:1.4rem 0 .7rem}
.sec h3{font-size:1.15rem;font-weight:800;margin:0;padding:0}.sec span{color:var(--muted);font-size:.85rem;font-weight:600}
/* cards */
[class*="st-key-card"],[data-testid="stForm"]{background:#fff;border:0;border-radius:24px;padding:1.2rem 1.3rem;box-shadow:0 6px 24px rgba(124,102,214,.07)}
[data-testid="stForm"]{padding:1.4rem 1.5rem}
[data-testid="stMetric"]{background:#fff;border-radius:20px;padding:1rem 1.2rem;box-shadow:0 6px 24px rgba(124,102,214,.07)}
[data-testid="stDataFrame"]{border-radius:18px;overflow:hidden;border:1px solid var(--line)}
[data-testid="stAlert"]{border-radius:16px;border:0}
hr{border-color:var(--line)!important;margin:1.4rem 0!important}
/* stat cards */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-bottom:.4rem}
.stat{background:#fff;border-radius:22px;padding:1rem 1.1rem;display:flex;align-items:center;gap:.9rem;box-shadow:0 6px 24px rgba(124,102,214,.07)}
.stat .v{font-size:1.55rem;font-weight:800;line-height:1.1}.stat .l{color:var(--muted);font-size:.84rem;font-weight:600}
.stat .n{font-size:.76rem;font-weight:700;margin-top:.15rem}
.tile{width:48px;height:48px;border-radius:16px;display:grid;place-items:center;flex:none}
.t-purple{background:var(--ps);color:var(--p)}.t-pink{background:var(--ks);color:#E0707F}.t-blue{background:var(--bs);color:var(--b)}.t-green{background:var(--gs);color:var(--g)}.t-teal{background:var(--ts);color:#5E9395}
.c-purple{color:var(--pd)}.c-pink{color:var(--kd)}.c-blue{color:var(--bd)}.c-green{color:var(--gd)}.c-teal{color:#3E5757}
/* chips */
.chip{display:inline-block;border-radius:999px;padding:.18rem .65rem;font-size:.75rem;font-weight:700;white-space:nowrap}
.ch-purple{background:var(--ps);color:var(--pd)}.ch-pink{background:var(--ks);color:var(--kd)}.ch-blue{background:var(--bs);color:var(--bd)}.ch-green{background:var(--gs);color:var(--gd)}.ch-teal{background:var(--ts);color:#3E5757}
/* rows */
.rows{display:flex;flex-direction:column;gap:.55rem}
.row{display:flex;align-items:center;gap:.85rem;background:var(--canvas);border-radius:18px;padding:.7rem .85rem}
.row .tile{width:40px;height:40px;border-radius:13px}
.row .tx{flex:1;min-width:0}.row b{display:block;font-size:.92rem;line-height:1.25;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row small{color:var(--muted);font-size:.78rem}
.empty{text-align:center;padding:1.6rem 1rem;color:var(--muted);font-size:.9rem;background:var(--canvas);border-radius:18px}
.empty .ms{font-size:34px;color:var(--t);display:block;margin-bottom:.3rem}
/* stock bars */
.sb{margin:.2rem 0 .8rem}.sb .h{display:flex;justify-content:space-between;font-size:.86rem;font-weight:700;margin-bottom:.3rem}
.sb .h span{color:var(--muted);font-weight:600}
.bar{height:10px;border-radius:99px;background:var(--canvas);overflow:hidden}.bar i{display:block;height:100%;border-radius:99px}
/* calendar */
.cal{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));min-width:0;gap:.15rem;text-align:center;font-size:.85rem;font-weight:600}
.cal .w{color:#8a9494;font-size:.72rem;padding:.2rem 0 .4rem}.cal .d{position:relative;min-width:0;width:100%;max-width:2.6rem;margin:0 auto;padding:.5rem 0;border-radius:50%;aspect-ratio:1;display:grid;place-items:center}
.cal .o{color:#b7bdc4}.cal .td{background:var(--p);color:#fff}
.cal .d i{position:absolute;bottom:3px;width:5px;height:5px;border-radius:50%;background:var(--k)}
.cal .d i.m{background:var(--g)}.cal .d i.h{background:var(--p)}.cal .td i{background:#fff}
.cal-t{font-weight:800;font-size:1rem;padding-top:.35rem;white-space:nowrap}
[class*="st-key-cal_"] button{padding:.35rem .6rem!important}
/* patient */
.pt{display:flex;gap:1rem;align-items:center}.pt h4{margin:0;font-size:1.1rem}.pt small{color:var(--muted)}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.6rem;margin-top:1rem}
.fact{background:var(--canvas);border-radius:16px;padding:.6rem .8rem}.fact small{display:block;color:var(--muted);font-size:.74rem;font-weight:600}.fact b{font-size:.92rem}
.warn{margin-top:.9rem;background:var(--ks);color:var(--kd);border-radius:16px;padding:.7rem .9rem;font-weight:700;font-size:.88rem}
/* stepper */
.steps{display:flex;gap:.4rem;margin:.2rem 0 1rem}.step{flex:1;text-align:center;font-size:.8rem;font-weight:700;padding:.55rem .3rem;border-radius:14px;background:var(--canvas);color:#8a9494}
.step.done{background:var(--gs);color:var(--gd)}.step.now{background:var(--p);color:#fff}
/* insight */
.ins{display:flex;gap:.8rem;align-items:center}.ins b{font-size:1rem;display:block}.ins small{color:var(--muted);font-weight:600}
/* inputs */
[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{border-radius:14px!important;border-color:transparent!important;background:var(--canvas)!important}
[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within,[data-baseweb="select"]>div:focus-within{box-shadow:0 0 0 2px var(--p)!important}
[data-baseweb="tag"]{background:var(--ps)!important;color:var(--pd)!important;border-radius:10px!important}
.stApp label p{font-weight:600;font-size:.88rem}
/* buttons */
[data-testid="stBaseButton-secondary"],[data-testid="stBaseButton-secondaryFormSubmit"],[data-testid="stDownloadButton"] button{border-radius:999px;border:1px solid var(--line);background:#fff;font-weight:700;padding:.45rem 1.2rem;color:var(--ink)}
[data-testid="stBaseButton-secondary"]:hover,[data-testid="stDownloadButton"] button:hover{border-color:var(--p);color:var(--pd);background:#fff}
[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"]{border-radius:999px;border:0;font-weight:700;padding:.5rem 1.5rem;background:linear-gradient(135deg,#8E78E8,#6A55C9);box-shadow:0 8px 18px rgba(124,102,214,.3)}
/* tabs */
[data-baseweb="tab-list"]{gap:.35rem;background:#fff;padding:.35rem;border-radius:999px;width:fit-content;max-width:100%;overflow-x:auto;box-shadow:0 4px 16px rgba(124,102,214,.07)}
[data-baseweb="tab"]{border-radius:999px!important;padding:.45rem 1.1rem!important;height:auto!important;color:var(--muted)}
[data-baseweb="tab"][aria-selected="true"]{background:var(--p)!important;color:#fff!important}
[data-baseweb="tab"][aria-selected="true"] p{color:#fff}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"]{display:none}
[data-testid="stTabPanel"]{padding-top:1.2rem}
/* login */
.hero{border-radius:32px;padding:2.4rem;min-height:620px;color:#fff;background:radial-gradient(420px 300px at 90% 95%,rgba(189,215,216,.9),transparent 70%),linear-gradient(150deg,#6F59CC 0%,#9A82E6 48%,#F7CBCA 100%);box-shadow:0 20px 50px rgba(124,102,214,.28);display:flex;flex-direction:column;justify-content:space-between;gap:2rem}
.hero .brand b{color:#fff}.hero .brand small{color:#EDE8FF}.hero .brand .logo{background:rgba(255,255,255,.22);box-shadow:none}
.hero h1{color:#fff;font-size:2.7rem;line-height:1.08;font-weight:800;margin:0 0 .8rem;padding:0;max-width:14ch}
.hero p{color:#F3EFFF;font-size:1.02rem;max-width:38ch;margin:0}
.feat{display:flex;flex-direction:column;gap:.7rem}.feat .row{background:rgba(255,255,255,.92);color:var(--ink)}
.login-h{font-size:1.6rem;font-weight:800;margin:.2rem 0 .2rem}.login-s{color:var(--muted);margin-bottom:1rem;font-size:.92rem}
@media (max-width:900px){.block-container{padding:1.2rem 1rem 3rem}.hero{min-height:auto}.hero h1{font-size:2.1rem}}
@media (prefers-reduced-motion:no-preference){.hero{animation:rise .6s ease both}@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}}
"""


def esc(x):
    return html.escape("" if x is None else str(x))


def ms(name):
    return f'<span class="ms">{name}</span>'


def tile(icon, tone="purple"):
    return f'<div class="tile t-{tone}">{ms(icon)}</div>'


def initials(nama):
    parts = [p for p in str(nama or "?").split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def chip(text, tone="purple"):
    return f'<span class="chip ch-{tone}">{esc(text)}</span>'


def status_chip(status):
    return chip(status, STATUS_TONE.get(status, "teal"))


def html_block(s):
    """Markdown menganggap baris berindent / baris kosong sebagai kode, jadi HTML dipadatkan."""
    st.markdown(re.sub(r"\s*\n\s*", "", s), unsafe_allow_html=True)


# ------------------------------------------------------------------ LOGO
_HERE = Path(__file__).resolve().parent
ASSETS = next((p for p in (_HERE / "assets", _HERE.parent / "assets") if p.exists()),
              _HERE.parent / "assets")


@st.cache_resource(show_spinner=False)
def _asset_uri(name):
    """Logo disisipkan sebagai data-URI, jadi ikut tampil saat deploy tanpa server file statis."""
    p = ASSETS / name
    if not p.exists():
        return None, 0, 0
    from PIL import Image
    with Image.open(p) as im:
        w, h = im.size
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode(), w, h


@st.cache_resource(show_spinner=False)
def _favicon():
    p = ASSETS / "favicon.png"
    if not p.exists():
        return None
    from PIL import Image
    with Image.open(p) as im:
        return im.copy()


def brand_html():
    """Logo ITSB Health untuk sidebar. Kalau file logo tidak ada, pakai ikon bawaan."""
    uri, _, _ = _asset_uri("logo_web.png")
    if not uri:
        return (f'<div class="brand"><div class="logo">{ms("health_and_safety")}</div>'
                f'<div><b>UKS Kampus</b><small>Layanan kesehatan</small></div></div>')
    return (f'<div class="brandlogo"><img src="{uri}" alt="ITSB Health"></div>'
            f'<div class="brandcap">Layanan Kesehatan Kampus</div>')


# ------------------------------------------------------------------ SETUP
def setup(title, icon, roles=None, sidebar=True, narrow=False):
    fav = _favicon()
    st.set_page_config(page_title=f"{title} · UKS", page_icon=fav if fav is not None else icon, layout="wide",
                       initial_sidebar_state="expanded" if sidebar else "collapsed")
    st.session_state["_ck"] = 0
    st.session_state["_pk"] = 0
    css = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    css = re.sub(r"\s*\n\s*", "", css)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    if not sidebar:
        st.markdown('<span class="nosb-flag"></span>', unsafe_allow_html=True)
        st.markdown("<style>.stApp:has(.nosb-flag) [data-testid='stSidebar'],.stApp:has(.nosb-flag) "
                    "[data-testid='stSidebarCollapsedControl'],.stApp:has(.nosb-flag) "
                    "[data-testid='stExpandSidebarButton']{display:none}</style>", unsafe_allow_html=True)
    if not sidebar:
        uri, w, h = _asset_uri("logo_web.png")
        if uri:
            ratio = 1 / (0.82 * h / w + 0.18)
            st.markdown(
                "<style>.hero .brand>*{display:none}"
                ".hero .brand::before{content:'';display:block;width:min(100%,250px);"
                f"aspect-ratio:{ratio:.3f};border-radius:22px;"
                f"background:#fff url({uri}) center/82% no-repeat;"
                "box-shadow:0 12px 28px rgba(38,43,61,.2)}</style>", unsafe_allow_html=True)
    if narrow:
        st.markdown("<style>.block-container{max-width:900px!important}</style>", unsafe_allow_html=True)
    if sidebar:
        _sidebar()
    role = st.session_state.get("role")
    if roles is not None and role not in roles:
        _gate(role)


def _gate(role):
    with card():
        if not role:
            html_block(f'<div class="empty">{ms("lock")}<b>Kamu belum masuk.</b><br>Masuk dulu untuk membuka halaman ini.</div>')
        else:
            html_block(f'<div class="empty">{ms("block")}<b>Halaman ini bukan untuk role {esc(ROLE_LABEL.get(role, role))}.</b><br>Pilih menu lain di sebelah kiri.</div>')
        st.page_link("app.py", label="Ke beranda", icon=":material/home:")
    st.stop()


def _sidebar():
    role = st.session_state.get("role")
    nama = st.session_state.get("nama", "")
    menu = [("app.py", "Beranda", "home")]
    if role == "mahasiswa":
        menu.append(("pages/1_Mahasiswa.py", "Form keluhan", "edit_note"))
    if role == "petugas":
        menu += [("pages/2_Petugas.py", "Layani pasien", "stethoscope"),
                 ("pages/5_Dashboard.py", "Dashboard", "monitoring")]
    if role == "admin":
        menu += [("pages/3_Admin.py", "Panel admin", "admin_panel_settings"),
                 ("pages/5_Dashboard.py", "Dashboard", "monitoring")]
    if role == "mitra":
        menu.append(("pages/4_Mitra.py", "Rujukan masuk", "local_hospital"))
    with st.sidebar:
        html_block(brand_html())
        if role:
            for path, label, ic in menu:
                st.page_link(path, label=label, icon=f":material/{ic}:")
            html_block(f'<div class="me"><div class="av">{esc(initials(nama))}</div>'
                       f'<div><b>{esc(nama)}</b><small>{esc(ROLE_LABEL.get(role, role))}</small></div></div>')
            if st.button("Keluar", icon=":material/logout:", key="btn_logout"):
                st.session_state.clear()
                st.switch_page("app.py")


def header(title, subtitle=""):
    d = date.today()
    nama = st.session_state.get("nama")
    who = (f'<div class="pill"><div class="av">{esc(initials(nama))}</div>{esc(nama)}</div>' if nama else "")
    html_block(f'<div class="top"><div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>'
               f'<div style="display:flex;gap:.6rem;flex-wrap:wrap;align-items:center">'
               f'<div class="pill date">{ms("calendar_month")}&nbsp;{HARI[d.weekday()]}, {d.day} {BULAN[d.month-1]} {d.year}</div>{who}</div></div>')


def section(title, note=""):
    html_block(f'<div class="sec"><h3>{esc(title)}</h3><span>{esc(note)}</span></div>')


def card():
    st.session_state["_ck"] = st.session_state.get("_ck", 0) + 1
    return st.container(border=True, key=f"card_{st.session_state['_ck']}")


# ------------------------------------------------------------- KOMPONEN
def stats(items):
    """items: (label, nilai, ikon, tone, catatan opsional)"""
    out = ""
    for it in items:
        label, val, ic, tone = it[:4]
        note = f'<div class="n c-{tone}">{esc(it[4])}</div>' if len(it) > 4 and it[4] else ""
        out += (f'<div class="stat">{tile(ic, tone)}<div><div class="v">{esc(val)}</div>'
                f'<div class="l">{esc(label)}</div>{note}</div></div>')
    html_block(f'<div class="stats">{out}</div>')


def rows(items, empty="Belum ada data."):
    """items: (ikon, tone, judul, sub, teks_chip, tone_chip)"""
    if not items:
        html_block(f'<div class="empty">{ms("inbox")}{esc(empty)}</div>')
        return
    out = ""
    for ic, tone, title, sub, ct, ctone in items:
        c = chip(ct, ctone) if ct else ""
        out += (f'<div class="row">{tile(ic, tone)}<div class="tx"><b>{esc(title)}</b>'
                f'<small>{esc(sub)}</small></div>{c}</div>')
    html_block(f'<div class="rows">{out}</div>')


def stock_bars(df, limit=None):
    """df punya kolom nama_obat, satuan, stok, stok_minimum"""
    out = ""
    for r in df.head(limit).itertuples() if limit else df.itertuples():
        low = r.stok <= r.stok_minimum
        cap = max(r.stok_minimum * 3, r.stok, 1)
        pct = min(100, round(r.stok / cap * 100))
        color = PINK if low else GREEN
        tag = chip("Menipis", "pink") if low else ""
        out += (f'<div class="sb"><div class="h"><div>{esc(r.nama_obat)} {tag}</div>'
                f'<span>{int(r.stok)} {esc(r.satuan)} · min {int(r.stok_minimum)}</span></div>'
                f'<div class="bar"><i style="width:{pct}%;background:{color}"></i></div></div>')
    html_block(out)


def patient_card(nama, sub, facts, alergi=None):
    fs = "".join(f'<div class="fact"><small>{esc(a)}</small><b>{esc(b)}</b></div>' for a, b in facts)
    al = f'<div class="warn">{ms("warning")}&nbsp; Riwayat alergi: {esc(alergi)}</div>' if alergi else ""
    html_block(f'<div class="pt"><div class="av lg">{esc(initials(nama))}</div>'
               f'<div><h4>{esc(nama)}</h4><small>{esc(sub)}</small></div></div>'
               f'<div class="facts">{fs}</div>{al}')


def stepper(steps, current):
    idx = steps.index(current) if current in steps else 0
    out = ""
    for i, s in enumerate(steps):
        cls = "done" if i < idx or current == "Selesai" else ("now" if i == idx else "")
        out += f'<div class="step {cls}">{esc(s)}</div>'
    html_block(f'<div class="steps">{out}</div>')


def insight(icon, tone, big, small):
    html_block(f'<div class="ins">{tile(icon, tone)}<div><b>{esc(big)}</b><small>{esc(small)}</small></div></div>')


def calendar_card(marks, key="cal", note="Titik menandai hari yang ada data"):
    """marks: dict {date: jumlah}. Ada tombol bulan sebelumnya / berikutnya."""
    off_key = f"{key}_off"
    st.session_state.setdefault(off_key, 0)

    def geser(n):
        st.session_state[off_key] += n

    today = date.today()
    total = today.year * 12 + today.month - 1 + st.session_state[off_key]
    y, m = divmod(total, 12)
    m += 1
    with card():
        c1, c2, c3 = st.columns([4, 1, 1], vertical_alignment="center")
        c1.markdown(f'<div class="cal-t">{BULAN[m-1]} {y}</div>', unsafe_allow_html=True)
        c2.button("", icon=":material/chevron_left:", key=f"{key}_p", on_click=geser, args=(-1,))
        c3.button("", icon=":material/chevron_right:", key=f"{key}_n", on_click=geser, args=(1,))
        cells = "".join(f'<div class="w">{h}</div>' for h in ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"])
        for d in calendar.Calendar(0).itermonthdates(y, m):
            n = marks.get(d, 0)
            cls = "d" + (" o" if d.month != m else "") + (" td" if d == today else "")
            dot = f'<i class="{"h" if n >= 6 else "m" if n >= 3 else ""}" title="{n}"></i>' if n else ""
            cells += f'<div class="{cls}">{d.day}{dot}</div>'
        html_block(f'<div class="cal">{cells}</div>')
        st.caption(note)


def plot(fig, h=300, legend=False):
    fig.update_layout(
        template="none", height=h, margin=dict(l=4, r=4, t=10, b=4),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", colorway=COLORWAY,
        font=dict(family="Plus Jakarta Sans, system-ui, sans-serif", color=INK, size=12),
        showlegend=legend, legend=dict(orientation="h", y=-0.18, title=None),
        hoverlabel=dict(bgcolor="#fff", bordercolor=LINE, font_color=INK),
    )
    fig.update_xaxes(showgrid=False, linecolor=LINE, title=None, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor="#E9EBF7", zeroline=False, title=None, tickfont=dict(color=MUTED))
    try:
        fig.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
    except Exception:
        pass
    st.session_state["_pk"] = st.session_state.get("_pk", 0) + 1
    st.plotly_chart(fig, theme=None, key=f"plot_{st.session_state['_pk']}",
                    config={"displayModeBar": False})