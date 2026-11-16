import streamlit as st
import pandas as pd
from db.connection import run_query
from utils import ui
from utils.auth import require_role

ui.setup("Rujukan Masuk", "🏥", roles=["mitra"])
require_role("mitra")

faskes_id = st.session_state.get("faskes_id")
if not faskes_id:
    st.error("Akun ini belum dikaitkan dengan faskes. Hubungi admin.")
    st.stop()

faskes = run_query("SELECT nama, jenis FROM faskes_mitra WHERE id = %s", (faskes_id,))[0]
ui.header(faskes["nama"], f"{faskes['jenis']} mitra UKS. Kamu hanya melihat rujukan yang ditujukan ke faskes ini.")

if "pesan_mitra" in st.session_state:
    st.success(st.session_state.pop("pesan_mitra"))

# urutan status yang diizinkan
ALUR = {
    "Dibuat": ["Diterima"],
    "Diterima": ["Ditangani"],
    "Ditangani": ["Selesai"],
    "Selesai": [],
}
IKON = {"Dibuat": "🆕", "Diterima": "📥", "Ditangani": "🩺", "Selesai": "✅"}

# ---------- Ringkasan ----------
hitung = run_query(
    "SELECT status, COUNT(*) AS n FROM rujukan WHERE faskes_id = %s GROUP BY status",
    (faskes_id,),
)
jumlah = {h["status"]: h["n"] for h in hitung}
ICON = {"Dibuat": ("mark_email_unread", "pink"), "Diterima": ("inbox", "blue"),
        "Ditangani": ("stethoscope", "purple"), "Selesai": ("check_circle", "green")}
ui.stats([(s, jumlah.get(s, 0), *ICON[s]) for s in ALUR])

# ---------- Filter ----------
st.divider()
filter_status = st.radio(
    "Tampilkan", ["Aktif (belum selesai)", "Selesai", "Semua"], horizontal=True
)
kondisi = {
    "Aktif (belum selesai)": "AND r.status <> 'Selesai'",
    "Selesai": "AND r.status = 'Selesai'",
    "Semua": "",
}[filter_status]

rujukan = run_query(
    f"""SELECT r.id, r.created_at, r.status, u.nama, m.nim, k.keluhan_utama
        FROM rujukan r
        JOIN pelayanan p ON p.id = r.pelayanan_id
        JOIN keluhan k ON k.id = p.keluhan_id
        JOIN mahasiswa m ON m.user_id = k.mahasiswa_id
        JOIN users u ON u.id = m.user_id
        WHERE r.faskes_id = %s {kondisi}
        ORDER BY r.created_at DESC""",
    (faskes_id,),
)

if not rujukan:
    st.info("Tidak ada rujukan pada kategori ini.")
    st.stop()

df = pd.DataFrame(rujukan)
df["status"] = df["status"].map(lambda s: f"{IKON[s]} {s}")
st.dataframe(
    df.drop(columns=["id"]).rename(columns={
        "created_at": "Tanggal rujukan", "status": "Status", "nama": "Mahasiswa",
        "nim": "NIM", "keluhan_utama": "Keluhan"}),
    hide_index=True,
)

# ---------- Detail & update ----------
pilihan = {
    f"#{r['id']} - {r['nama']} ({r['status']})": r["id"] for r in rujukan
}
terpilih = st.selectbox("Pilih rujukan untuk dilihat / diperbarui", list(pilihan.keys()))
rid = pilihan[terpilih]

# filter faskes_id lagi di sini, supaya faskes lain tidak bisa mengakses rujukan ini
d = run_query(
    """SELECT r.*, u.nama, u.email, m.nim, m.prodi, m.angkatan, m.no_hp,
              k.kode, k.keluhan_utama, k.lama_keluhan, k.tingkat_nyeri,
              k.gejala_lain, k.riwayat_alergi,
              p.diagnosis_awal, p.tindakan, p.tanggal AS tgl_pelayanan
       FROM rujukan r
       JOIN pelayanan p ON p.id = r.pelayanan_id
       JOIN keluhan k ON k.id = p.keluhan_id
       JOIN mahasiswa m ON m.user_id = k.mahasiswa_id
       JOIN users u ON u.id = m.user_id
       WHERE r.id = %s AND r.faskes_id = %s""",
    (rid, faskes_id),
)
if not d:
    st.error("Rujukan tidak ditemukan.")
    st.stop()
d = d[0]

obat = run_query(
    """SELECT o.nama_obat, po.jumlah, o.satuan
       FROM pelayanan_obat po JOIN obat o ON o.id = po.obat_id
       WHERE po.pelayanan_id = %s""",
    (d["pelayanan_id"],),
)

st.divider()
ui.section(f"Detail rujukan #{d['id']}", d["status"])
ui.stepper(list(ALUR.keys()), d["status"])

c1, c2 = st.columns(2)
with c1:
    st.markdown("**👤 Data Mahasiswa**")
    st.write(f"Nama: {d['nama']}")
    st.write(f"NIM: {d['nim']}")
    st.write(f"Prodi / angkatan: {d['prodi'] or '-'} / {d['angkatan'] or '-'}")
    st.write(f"No. HP: {d['no_hp'] or '-'}")
    st.markdown("**📝 Keluhan**")
    st.write(f"Keluhan utama: {d['keluhan_utama']}")
    st.write(f"Lama: {d['lama_keluhan']}  |  Nyeri: {d['tingkat_nyeri']}/10")
    st.write(f"Gejala lain: {d['gejala_lain'] or '-'}")
    if d["riwayat_alergi"] and d["riwayat_alergi"] != "Tidak ada":
        st.warning(f"⚠️ Riwayat alergi: {d['riwayat_alergi']}")
with c2:
    st.markdown("**🩺 Penanganan di UKS**")
    st.write(f"Diagnosis awal: {d['diagnosis_awal']}")
    st.write(f"Tindakan: {d['tindakan'] or '-'}")
    if obat:
        st.write("Obat yang sudah diberikan: " +
                 ", ".join(f"{o['nama_obat']} x{o['jumlah']} {o['satuan']}" for o in obat))
    else:
        st.write("Obat yang sudah diberikan: -")
    st.markdown("**📨 Rujukan**")
    st.write(f"Alasan: {d['alasan_rujukan']}")
    st.write(f"Dibuat: {d['created_at']:%d-%m-%Y %H:%M}")
    st.write(f"Pembaruan terakhir: {d['updated_at']:%d-%m-%Y %H:%M}")

st.markdown("**📋 Catatan tindak lanjut**")
st.write(d["catatan_tindak_lanjut"] or "_Belum ada catatan._")

# ---------- Form update ----------
st.divider()
ui.section("Perbarui Status")
berikutnya = ALUR[d["status"]]
if not berikutnya:
    st.success("Rujukan ini sudah selesai.")
else:
    with st.form(f"update_{rid}"):
        status_baru = st.selectbox("Status baru", berikutnya)
        catatan = st.text_area(
            "Catatan tindak lanjut",
            value=d["catatan_tindak_lanjut"] or "",
            help="Catatan lama akan diganti dengan isi kolom ini.",
        )
        simpan = st.form_submit_button("Simpan Pembaruan", type="primary")

    if simpan:
        if status_baru == "Selesai" and not catatan.strip():
            st.error("Catatan tindak lanjut wajib diisi sebelum menyelesaikan rujukan.")
        else:
            run_query(
                """UPDATE rujukan SET status = %s, catatan_tindak_lanjut = %s
                   WHERE id = %s AND faskes_id = %s""",
                (status_baru, catatan.strip() or None, rid, faskes_id),
                fetch=False,
            )
            if status_baru == "Selesai":
                run_query(
                    """UPDATE keluhan SET status = 'Selesai' WHERE id = (
                           SELECT p.keluhan_id FROM pelayanan p
                           JOIN rujukan r ON r.pelayanan_id = p.id WHERE r.id = %s)""",
                    (rid,),
                    fetch=False,
                )
            st.session_state["pesan_mitra"] = f"Status rujukan #{rid} diperbarui menjadi {status_baru}."
            st.rerun()