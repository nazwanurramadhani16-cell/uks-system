import streamlit as st
import pandas as pd
from datetime import date
from db.connection import run_query, get_connection
from utils import ui
from utils.auth import require_role, hash_password

ui.setup("Panel Admin", "🛠️", roles=["admin"])
require_role("admin")

ui.header("Panel admin", "Kelola stok obat, akun staf, dan faskes mitra.")

# pesan sukses yang tetap tampil setelah halaman di-refresh
if "pesan_admin" in st.session_state:
    st.success(st.session_state.pop("pesan_admin"))


def selesai(pesan):
    st.session_state["pesan_admin"] = pesan
    st.rerun()


def catat_obat_masuk(obat_id, jumlah, tgl_masuk, tgl_kadaluarsa, admin_id):
    """Catat obat masuk + tambah stok sekaligus. Kalau salah satu gagal, dibatalkan."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO obat_masuk (obat_id, jumlah, tanggal_masuk, tanggal_kadaluarsa, dicatat_oleh)
               VALUES (%s, %s, %s, %s, %s)""",
            (obat_id, jumlah, tgl_masuk, tgl_kadaluarsa, admin_id),
        )
        cur.execute("UPDATE obat SET stok = stok + %s WHERE id = %s", (jumlah, obat_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


tab_stok, tab_masuk, tab_baru, tab_akun, tab_faskes = st.tabs(
    ["📦 Stok Obat", "➕ Obat Masuk", "💊 Obat Baru", "👥 Kelola Akun", "🏥 Faskes Mitra"]
)

# ---------------------------------------------------------------- STOK
with tab_stok:
    obat = run_query(
        "SELECT id, nama_obat, kategori, satuan, stok, stok_minimum FROM obat ORDER BY nama_obat"
    )
    if not obat:
        st.info("Belum ada data obat.")
    else:
        df = pd.DataFrame(obat)
        df["status"] = df.apply(
            lambda r: "⚠️ Menipis" if r["stok"] <= r["stok_minimum"] else "✅ Aman", axis=1
        )
        menipis = int((df["status"] == "⚠️ Menipis").sum())

        ui.stats([("Jenis obat", len(df), "medication", "purple"),
                  ("Stok menipis", menipis, "warning", "pink"),
                  ("Total unit", int(df["stok"].sum()), "inventory_2", "green")])

        if menipis:
            st.warning("Obat berikut perlu segera ditambah: " +
                       ", ".join(df[df["status"] == "⚠️ Menipis"]["nama_obat"]))

        ui.section("Kondisi stok", "bar pink = di bawah batas minimum")
        with ui.card():
            ui.stock_bars(df)
        with st.expander("Lihat tabel lengkap"):
            st.dataframe(
                df.drop(columns=["id"]).rename(columns={
                    "nama_obat": "Nama obat", "kategori": "Kategori", "satuan": "Satuan",
                    "stok": "Stok", "stok_minimum": "Stok minimum", "status": "Status"}),
                hide_index=True,
            )

    ui.section("Batch Mendekati / Sudah Kadaluarsa")
    kadaluarsa = run_query(
        """SELECT o.nama_obat AS obat, om.jumlah AS jumlah_masuk,
                  om.tanggal_masuk, om.tanggal_kadaluarsa,
                  DATEDIFF(om.tanggal_kadaluarsa, CURDATE()) AS sisa_hari
           FROM obat_masuk om JOIN obat o ON o.id = om.obat_id
           WHERE om.tanggal_kadaluarsa IS NOT NULL
             AND om.tanggal_kadaluarsa <= DATE_ADD(CURDATE(), INTERVAL 60 DAY)
           ORDER BY om.tanggal_kadaluarsa"""
    )
    if kadaluarsa:
        st.dataframe(pd.DataFrame(kadaluarsa), hide_index=True)
        st.caption("sisa_hari negatif = sudah kadaluarsa. Stok dihitung total per obat, "
                   "jadi tabel ini hanya pengingat batch yang masuk.")
    else:
        st.info("Tidak ada batch yang kadaluarsa dalam 60 hari ke depan.")

# ---------------------------------------------------------- OBAT MASUK
with tab_masuk:
    ui.section("Catat Obat Masuk")
    daftar = run_query("SELECT id, nama_obat, satuan, stok FROM obat ORDER BY nama_obat")
    if not daftar:
        st.info("Tambahkan obat dulu di tab **Obat Baru**.")
    else:
        info = {o["id"]: o for o in daftar}
        with st.form("form_masuk", clear_on_submit=True):
            obat_id = st.selectbox(
                "Obat", list(info.keys()),
                format_func=lambda i: f"{info[i]['nama_obat']} (stok: {info[i]['stok']} {info[i]['satuan']})",
            )
            jumlah = st.number_input("Jumlah masuk", min_value=1, value=10)
            tgl_masuk = st.date_input("Tanggal masuk", value=date.today())
            ada_exp = st.checkbox("Obat ini punya tanggal kadaluarsa", value=True)
            tgl_exp = st.date_input("Tanggal kadaluarsa", value=date.today().replace(year=date.today().year + 2))
            simpan = st.form_submit_button("Simpan", type="primary")

        if simpan:
            if ada_exp and tgl_exp <= tgl_masuk:
                st.error("Tanggal kadaluarsa harus setelah tanggal masuk.")
            else:
                try:
                    catat_obat_masuk(obat_id, int(jumlah), tgl_masuk,
                                     tgl_exp if ada_exp else None,
                                     st.session_state["user_id"])
                    selesai(f"{info[obat_id]['nama_obat']} +{int(jumlah)} berhasil dicatat. Stok sudah diperbarui.")
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")

    ui.section("Riwayat Obat Masuk (50 terbaru)")
    riwayat = run_query(
        """SELECT om.tanggal_masuk, o.nama_obat AS obat, om.jumlah,
                  om.tanggal_kadaluarsa, u.nama AS dicatat_oleh
           FROM obat_masuk om
           JOIN obat o ON o.id = om.obat_id
           JOIN users u ON u.id = om.dicatat_oleh
           ORDER BY om.id DESC LIMIT 50"""
    )
    if riwayat:
        st.dataframe(pd.DataFrame(riwayat), hide_index=True)
    else:
        st.info("Belum ada catatan obat masuk.")

# ----------------------------------------------------------- OBAT BARU
with tab_baru:
    ui.section("Tambah Jenis Obat Baru")
    st.caption("Stok awal selalu 0. Isi stoknya lewat tab **Obat Masuk** supaya tercatat.")
    with st.form("form_obat_baru", clear_on_submit=True):
        nama_obat = st.text_input("Nama obat / perlengkapan *")
        kategori = st.text_input("Kategori", placeholder="Contoh: Pereda nyeri")
        satuan = st.text_input("Satuan *", placeholder="tablet / botol / pcs / sachet")
        stok_min = st.number_input("Stok minimum (batas peringatan)", min_value=0, value=10)
        tambah = st.form_submit_button("Tambah Obat", type="primary")

    if tambah:
        if not nama_obat.strip() or not satuan.strip():
            st.error("Nama obat dan satuan wajib diisi.")
        elif run_query("SELECT id FROM obat WHERE nama_obat = %s", (nama_obat.strip(),)):
            st.error("Obat dengan nama itu sudah ada.")
        else:
            run_query(
                "INSERT INTO obat (nama_obat, kategori, satuan, stok, stok_minimum) VALUES (%s, %s, %s, 0, %s)",
                (nama_obat.strip(), kategori.strip(), satuan.strip(), int(stok_min)),
                fetch=False,
            )
            selesai(f"Obat '{nama_obat.strip()}' ditambahkan. Silakan isi stoknya di tab Obat Masuk.")

# ---------------------------------------------------------------- AKUN
with tab_akun:
    ui.section("Buat Akun Petugas / Admin / Mitra")
    faskes = run_query("SELECT id, nama, jenis FROM faskes_mitra ORDER BY nama")
    info_faskes = {f["id"]: f for f in faskes}

    role = st.selectbox("Role", ["petugas", "mitra", "admin"], key="akun_role")
    with st.form("form_akun", clear_on_submit=True):
        nama_a = st.text_input("Nama *")
        email_a = st.text_input("Email *")
        pw_a = st.text_input("Password awal * (min. 6 karakter)", type="password")
        faskes_a = None
        if role == "mitra":
            if info_faskes:
                faskes_a = st.selectbox(
                    "Faskes", list(info_faskes.keys()),
                    format_func=lambda i: f"{info_faskes[i]['nama']} ({info_faskes[i]['jenis']})",
                )
            else:
                st.warning("Tambahkan faskes dulu di tab **Faskes Mitra**.")
        buat = st.form_submit_button("Buat Akun", type="primary")

    if buat:
        if not (nama_a.strip() and email_a.strip() and pw_a):
            st.error("Nama, email, dan password wajib diisi.")
        elif len(pw_a) < 6:
            st.error("Password minimal 6 karakter.")
        elif role == "mitra" and not faskes_a:
            st.error("Akun mitra harus dikaitkan dengan faskes.")
        elif run_query("SELECT id FROM users WHERE email = %s", (email_a.strip(),)):
            st.error("Email sudah terdaftar.")
        else:
            run_query(
                """INSERT INTO users (nama, email, password_hash, role, faskes_id)
                   VALUES (%s, %s, %s, %s, %s)""",
                (nama_a.strip(), email_a.strip(), hash_password(pw_a), role, faskes_a),
                fetch=False,
            )
            selesai(f"Akun {role} untuk {nama_a.strip()} berhasil dibuat.")

    ui.section("Daftar Akun Staf & Mitra")
    akun = run_query(
        """SELECT u.id, u.nama, u.email, u.role, f.nama AS faskes, u.created_at AS dibuat
           FROM users u LEFT JOIN faskes_mitra f ON f.id = u.faskes_id
           WHERE u.role <> 'mahasiswa' ORDER BY u.role, u.nama"""
    )
    st.dataframe(pd.DataFrame(akun).drop(columns=["id"]), hide_index=True)

    jml_mhs = run_query("SELECT COUNT(*) AS n FROM users WHERE role = 'mahasiswa'")[0]["n"]
    st.caption(f"Jumlah mahasiswa terdaftar: {jml_mhs}")

# --------------------------------------------------------------- FASKES
with tab_faskes:
    ui.section("Tambah Faskes Mitra")
    with st.form("form_faskes", clear_on_submit=True):
        nama_f = st.text_input("Nama faskes *")
        jenis_f = st.selectbox("Jenis", ["Puskesmas", "RS"])
        alamat_f = st.text_area("Alamat")
        kontak_f = st.text_input("Kontak")
        tambah_f = st.form_submit_button("Tambah Faskes", type="primary")

    if tambah_f:
        if not nama_f.strip():
            st.error("Nama faskes wajib diisi.")
        else:
            run_query(
                "INSERT INTO faskes_mitra (nama, jenis, alamat, kontak) VALUES (%s, %s, %s, %s)",
                (nama_f.strip(), jenis_f, alamat_f.strip(), kontak_f.strip()),
                fetch=False,
            )
            selesai(f"Faskes '{nama_f.strip()}' ditambahkan.")

    ui.section("Daftar Faskes")
    data_f = run_query("SELECT nama, jenis, alamat, kontak FROM faskes_mitra ORDER BY nama")
    st.dataframe(pd.DataFrame(data_f), hide_index=True)