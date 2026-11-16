import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import date

from db.connection import run_query
from utils.auth import login, hash_password
from utils import ui

if "role" not in st.session_state:
    st.session_state["role"] = None

masuk = bool(st.session_state["role"])
ui.setup("Beranda" if masuk else "Masuk", "🏥", sidebar=masuk)


# ============================================================ LOGIN
def halaman_login():
    kiri, kanan = st.columns([1.15, 1], gap="large")
    with kiri:
        ui.html_block(f'''
        <div class="hero">
          <div class="brand"><div class="logo">{ui.ms("health_and_safety")}</div>
            <div><b>UKS Kampus</b><small>Layanan kesehatan mahasiswa</small></div></div>
          <div><h1>Sakit di kampus? Catat dulu, tangani lebih cepat.</h1>
            <p>Isi keluhan dari HP sebelum ke UKS. Petugas langsung tahu kondisimu.</p></div>
          <div class="feat">
            <div class="row">{ui.tile("edit_note", "purple")}<div class="tx"><b>Isi keluhan dari mana saja</b><small>Tunjukkan kodenya ke petugas</small></div></div>
            <div class="row">{ui.tile("medication", "green")}<div class="tx"><b>Stok obat selalu terpantau</b><small>Ada peringatan saat hampir habis</small></div></div>
            <div class="row">{ui.tile("local_hospital", "blue")}<div class="tx"><b>Rujukan tercatat sampai selesai</b><small>Puskesmas dan RS mitra ikut memantau</small></div></div>
          </div>
        </div>''')
    with kanan:
        with ui.card():
            st.markdown('<div class="login-h">Selamat datang 👋</div>'
                        '<div class="login-s">Masuk untuk lanjut, atau daftar kalau kamu mahasiswa baru.</div>',
                        unsafe_allow_html=True)
            tab_login, tab_daftar = st.tabs(["Masuk", "Daftar (mahasiswa)"])
            with tab_login:
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_pw")
                if st.button("Masuk", type="primary", key="btn_masuk"):
                    user = login(email, password)
                    if user:
                        st.session_state["user_id"] = user["id"]
                        st.session_state["nama"] = user["nama"]
                        st.session_state["role"] = user["role"]
                        st.session_state["faskes_id"] = user["faskes_id"]
                        st.rerun()
                    else:
                        st.error("Email atau password salah.")
            with tab_daftar:
                form_daftar()


def form_daftar():
    nama = st.text_input("Nama lengkap", key="daftar_nama")
    c1, c2 = st.columns(2)
    nim = c1.text_input("NIM", key="daftar_nim")
    prodi = c2.text_input("Program studi", key="daftar_prodi")
    c3, c4 = st.columns(2)
    angkatan = c3.number_input("Angkatan", 2015, 2035, 2024, key="daftar_angkatan")
    no_hp = c4.text_input("No. HP", key="daftar_hp")
    email_d = st.text_input("Email", key="daftar_email")
    pw_d = st.text_input("Password (min. 6 karakter)", type="password", key="daftar_pw")

    if st.button("Daftar", type="primary", key="btn_daftar"):
        if not (nama and nim and email_d and pw_d):
            st.error("Nama, NIM, email, dan password wajib diisi.")
        elif len(pw_d) < 6:
            st.error("Password minimal 6 karakter.")
        elif run_query("SELECT id FROM users WHERE email = %s", (email_d,)):
            st.error("Email sudah terdaftar.")
        elif run_query("SELECT user_id FROM mahasiswa WHERE nim = %s", (nim,)):
            st.error("NIM sudah terdaftar.")
        else:
            uid = run_query(
                "INSERT INTO users (nama, email, password_hash, role) VALUES (%s, %s, %s, 'mahasiswa')",
                (nama, email_d, hash_password(pw_d)),
                fetch=False,
            )
            run_query(
                "INSERT INTO mahasiswa (user_id, nim, prodi, angkatan, no_hp) VALUES (%s, %s, %s, %s, %s)",
                (uid, nim, prodi, int(angkatan), no_hp),
                fetch=False,
            )
            st.success("Pendaftaran berhasil! Silakan masuk di tab Masuk.")


# ============================================================ BERANDA
def tgl(d):
    return d.strftime("%d-%m-%Y %H:%M") if hasattr(d, "hour") else str(d)


def grafik_14_hari(sql, params=(), judul="keluhan"):
    data = run_query(sql, params)
    s = pd.Series({r["d"]: r["n"] for r in data}, dtype="float")
    hari = pd.date_range(end=pd.Timestamp.today().normalize(), periods=14)
    df = pd.DataFrame({"tanggal": hari, "jumlah": [int(s.get(h.date(), 0)) for h in hari]})
    df["label"] = df["tanggal"].dt.strftime("%d/%m")
    fig = px.bar(df, x="label", y="jumlah", color_discrete_sequence=[ui.PURPLE])
    ui.plot(fig, h=260)
    return int(df["jumlah"].sum())


def beranda_staf(role):
    ui.header(f"Halo, {st.session_state['nama'].split()[0]}!",
              "Ini ringkasan UKS hari ini. Mulai dari antrean yang menunggu.")
    q = lambda sql: run_query(sql)[0]["n"]
    ui.stats([
        ("Keluhan hari ini", q("SELECT COUNT(*) n FROM keluhan WHERE DATE(tanggal) = CURDATE()"), "assignment", "purple"),
        ("Menunggu dilayani", q("SELECT COUNT(*) n FROM keluhan WHERE status = 'Menunggu'"), "hourglass_top", "pink"),
        ("Stok menipis", q("SELECT COUNT(*) n FROM obat WHERE stok <= stok_minimum"), "medication", "blue"),
        ("Rujukan aktif", q("SELECT COUNT(*) n FROM rujukan WHERE status <> 'Selesai'"), "local_hospital", "green"),
    ])

    marks = {r["d"]: r["n"] for r in run_query(
        "SELECT DATE(tanggal) d, COUNT(*) n FROM keluhan "
        "WHERE tanggal >= CURDATE() - INTERVAL 120 DAY GROUP BY DATE(tanggal)")}
    kiri, kanan = st.columns([2.1, 1], gap="large")
    with kiri:
        ui.section("Keluhan 14 hari terakhir")
        with ui.card():
            grafik_14_hari(
                "SELECT DATE(tanggal) d, COUNT(*) n FROM keluhan "
                "WHERE tanggal >= CURDATE() - INTERVAL 13 DAY GROUP BY DATE(tanggal)")
        a, b = st.columns(2, gap="large")
        with a:
            ui.section("Antrean terbaru")
            antre = run_query(
                """SELECT u.nama, k.keluhan_utama, k.tingkat_nyeri, k.tanggal FROM keluhan k
                   JOIN users u ON u.id = k.mahasiswa_id
                   WHERE k.status = 'Menunggu' ORDER BY k.tanggal LIMIT 5""")
            ui.rows([("person", "pink" if r["tingkat_nyeri"] >= 7 else "purple", r["nama"],
                      r["keluhan_utama"], f"Nyeri {r['tingkat_nyeri']}", "pink" if r["tingkat_nyeri"] >= 7 else "teal")
                     for r in antre], "Tidak ada antrean. Semua sudah dilayani.")
            if role == "petugas":
                st.page_link("pages/2_Petugas.py", label="Buka layanan pasien", icon=":material/arrow_forward:")
        with b:
            ui.section("Perlu ditambah")
            stok = pd.DataFrame(run_query(
                "SELECT nama_obat, satuan, stok, stok_minimum FROM obat "
                "WHERE stok <= stok_minimum ORDER BY stok / GREATEST(stok_minimum, 1) LIMIT 5"),
                columns=["nama_obat", "satuan", "stok", "stok_minimum"])
            if stok.empty:
                ui.rows([], "Semua stok obat di atas batas minimum.")
            else:
                with ui.card():
                    ui.stock_bars(stok)
    with kanan:
        ui.section("Kalender")
        ui.calendar_card(marks, "cal_staf", "Titik menandai hari yang ada keluhan masuk")
        ui.section("Rujukan aktif")
        rj = run_query(
            """SELECT u.nama, f.nama faskes, r.status FROM rujukan r
               JOIN pelayanan p ON p.id = r.pelayanan_id JOIN keluhan k ON k.id = p.keluhan_id
               JOIN users u ON u.id = k.mahasiswa_id JOIN faskes_mitra f ON f.id = r.faskes_id
               WHERE r.status <> 'Selesai' ORDER BY r.updated_at DESC LIMIT 4""")
        ui.rows([("local_hospital", ui.STATUS_TONE.get(r["status"], "blue"), r["nama"], r["faskes"],
                  r["status"], ui.STATUS_TONE.get(r["status"], "blue")) for r in rj], "Belum ada rujukan aktif.")


def beranda_mahasiswa():
    uid = st.session_state["user_id"]
    ui.header(f"Halo, {st.session_state['nama'].split()[0]}!",
              "Lagi kurang enak badan? Isi keluhanmu dulu sebelum ke UKS.")
    hitung = {r["status"]: r["n"] for r in run_query(
        "SELECT status, COUNT(*) n FROM keluhan WHERE mahasiswa_id = %s GROUP BY status", (uid,))}
    ui.stats([
        ("Total keluhan", sum(hitung.values()), "assignment", "purple"),
        ("Menunggu", hitung.get("Menunggu", 0), "hourglass_top", "pink"),
        ("Dirujuk", hitung.get("Dirujuk", 0), "local_hospital", "blue"),
        ("Selesai", hitung.get("Selesai", 0), "check_circle", "green"),
    ])
    marks = {r["d"]: r["n"] for r in run_query(
        "SELECT DATE(tanggal) d, COUNT(*) n FROM keluhan WHERE mahasiswa_id = %s GROUP BY DATE(tanggal)", (uid,))}
    kiri, kanan = st.columns([2.1, 1], gap="large")
    with kiri:
        ui.section("Keluhan terakhir")
        data = run_query(
            "SELECT kode, tanggal, keluhan_utama, status FROM keluhan "
            "WHERE mahasiswa_id = %s ORDER BY tanggal DESC LIMIT 6", (uid,))
        ui.rows([("sick", ui.STATUS_TONE.get(r["status"], "teal"), r["keluhan_utama"],
                  f"{r['kode']} · {tgl(r['tanggal'])}", r["status"], ui.STATUS_TONE.get(r["status"], "teal"))
                 for r in data], "Belum ada keluhan. Semoga sehat terus!")
        st.page_link("pages/1_Mahasiswa.py", label="Isi keluhan baru", icon=":material/add_circle:")
    with kanan:
        ui.section("Kalender")
        ui.calendar_card(marks, "cal_mhs", "Titik menandai hari kamu mengisi keluhan")


def beranda_mitra():
    fid = st.session_state.get("faskes_id")
    f = run_query("SELECT nama, jenis FROM faskes_mitra WHERE id = %s", (fid,)) if fid else []
    ui.header(f[0]["nama"] if f else "Mitra faskes",
              "Rujukan dari UKS yang ditujukan ke faskes ini." if f else "Akun ini belum dikaitkan dengan faskes. Hubungi admin.")
    if not f:
        return
    hitung = {r["status"]: r["n"] for r in run_query(
        "SELECT status, COUNT(*) n FROM rujukan WHERE faskes_id = %s GROUP BY status", (fid,))}
    ui.stats([("Baru dibuat", hitung.get("Dibuat", 0), "mark_email_unread", "pink"),
              ("Diterima", hitung.get("Diterima", 0), "inbox", "blue"),
              ("Ditangani", hitung.get("Ditangani", 0), "stethoscope", "purple"),
              ("Selesai", hitung.get("Selesai", 0), "check_circle", "green")])
    marks = {r["d"]: r["n"] for r in run_query(
        "SELECT DATE(created_at) d, COUNT(*) n FROM rujukan WHERE faskes_id = %s GROUP BY DATE(created_at)", (fid,))}
    kiri, kanan = st.columns([2.1, 1], gap="large")
    with kiri:
        ui.section("Rujukan terbaru")
        rj = run_query(
            """SELECT u.nama, k.keluhan_utama, r.status, r.created_at FROM rujukan r
               JOIN pelayanan p ON p.id = r.pelayanan_id JOIN keluhan k ON k.id = p.keluhan_id
               JOIN users u ON u.id = k.mahasiswa_id WHERE r.faskes_id = %s
               ORDER BY r.created_at DESC LIMIT 6""", (fid,))
        ui.rows([("person", ui.STATUS_TONE.get(r["status"], "teal"), r["nama"],
                  f"{r['keluhan_utama']} · {tgl(r['created_at'])}", r["status"],
                  ui.STATUS_TONE.get(r["status"], "teal")) for r in rj], "Belum ada rujukan.")
        st.page_link("pages/4_Mitra.py", label="Kelola rujukan", icon=":material/arrow_forward:")
    with kanan:
        ui.section("Kalender")
        ui.calendar_card(marks, "cal_mitra", "Titik menandai hari ada rujukan masuk")


# ============================================================ ROUTER
if not masuk:
    halaman_login()
else:
    role = st.session_state["role"]
    if role in ("petugas", "admin"):
        beranda_staf(role)
    elif role == "mahasiswa":
        beranda_mahasiswa()
    else:
        beranda_mitra()
