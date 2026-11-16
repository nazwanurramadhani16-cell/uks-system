import streamlit as st
import pandas as pd
from db.connection import run_query, get_connection
from utils import ui
from utils.auth import require_role

ui.setup("Layani Pasien", "👩‍⚕️", roles=["petugas"])
require_role("petugas")

ui.header("Layani pasien", "Pilih keluhan dari antrean, catat pemeriksaan, lalu beri obat atau rujukan.")


def simpan_pelayanan(keluhan_id, petugas_id, diagnosis, tindakan,
                     obat_dipakai, faskes_id, alasan):
    """Semua langkah disimpan sekaligus. Kalau satu gagal, semuanya dibatalkan."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO pelayanan (keluhan_id, petugas_id, diagnosis_awal, tindakan)
               VALUES (%s, %s, %s, %s)""",
            (keluhan_id, petugas_id, diagnosis, tindakan),
        )
        pelayanan_id = cur.lastrowid

        for obat_id, jumlah in obat_dipakai:
            # stok hanya berkurang kalau cukup
            cur.execute(
                "UPDATE obat SET stok = stok - %s WHERE id = %s AND stok >= %s",
                (jumlah, obat_id, jumlah),
            )
            if cur.rowcount == 0:
                raise ValueError("Stok obat tidak mencukupi.")
            cur.execute(
                """INSERT INTO pelayanan_obat (pelayanan_id, obat_id, jumlah)
                   VALUES (%s, %s, %s)""",
                (pelayanan_id, obat_id, jumlah),
            )

        if faskes_id:
            cur.execute(
                """INSERT INTO rujukan (pelayanan_id, faskes_id, alasan_rujukan)
                   VALUES (%s, %s, %s)""",
                (pelayanan_id, faskes_id, alasan),
            )

        status = "Dirujuk" if faskes_id else "Selesai"
        cur.execute("UPDATE keluhan SET status = %s WHERE id = %s", (status, keluhan_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def layani_pasien():
    if "pesan" in st.session_state:
        st.success(st.session_state.pop("pesan"))

    cari = st.text_input("🔍 Cari kode keluhan atau NIM", placeholder="Contoh: UKS-AB12CD atau 12345678")

    antrean = run_query(
        """SELECT k.id, k.kode, k.tanggal, u.nama, m.nim, k.keluhan_utama, k.tingkat_nyeri
           FROM keluhan k
           JOIN mahasiswa m ON m.user_id = k.mahasiswa_id
           JOIN users u ON u.id = m.user_id
           WHERE k.status = 'Menunggu' AND (k.kode LIKE %s OR m.nim LIKE %s)
           ORDER BY k.tanggal""",
        (f"%{cari}%", f"%{cari}%"),
    )

    ui.section("Antrean keluhan", f"{len(antrean)} menunggu")
    if not antrean:
        st.info("Tidak ada keluhan yang menunggu.")
        return

    ui.rows([("person", "pink" if a["tingkat_nyeri"] >= 7 else "purple", a["nama"],
              f"{a['keluhan_utama']} · {a['kode']} · NIM {a['nim']}",
              f"Nyeri {a['tingkat_nyeri']}", "pink" if a["tingkat_nyeri"] >= 7 else "teal")
             for a in antrean])
    st.write("")

    pilihan = {f"{a['kode']} - {a['nama']} ({a['keluhan_utama']})": a["id"] for a in antrean}
    terpilih = st.selectbox("Pilih keluhan yang akan dilayani", list(pilihan.keys()))
    keluhan_id = pilihan[terpilih]

    k = run_query(
        """SELECT k.*, u.nama, m.nim, m.prodi FROM keluhan k
           JOIN mahasiswa m ON m.user_id = k.mahasiswa_id
           JOIN users u ON u.id = m.user_id WHERE k.id = %s""",
        (keluhan_id,),
    )[0]

    ui.section("Detail keluhan")
    with ui.card():
        ada_alergi = k["riwayat_alergi"] and k["riwayat_alergi"] != "Tidak ada"
        ui.patient_card(
            k["nama"], f"NIM {k['nim']} · {k['prodi'] or '-'}",
            [("Keluhan utama", k["keluhan_utama"]), ("Sudah berapa lama", k["lama_keluhan"]),
             ("Tingkat nyeri", f"{k['tingkat_nyeri']}/10"), ("Gejala lain", k["gejala_lain"] or "-")],
            k["riwayat_alergi"] if ada_alergi else None)
    ui.section("Pemeriksaan & Tindakan")
    diagnosis = st.text_input("Diagnosis awal *", key=f"diag_{keluhan_id}")
    tindakan = st.text_area("Tindakan", key=f"tind_{keluhan_id}")

    # ----- Obat -----
    st.markdown("**💊 Obat / perlengkapan yang diberikan**")
    daftar_obat = run_query(
        "SELECT id, nama_obat, satuan, stok FROM obat WHERE stok > 0 ORDER BY nama_obat"
    )
    info_obat = {o["id"]: o for o in daftar_obat}
    pilih_obat = st.multiselect(
        "Pilih obat",
        options=list(info_obat.keys()),
        format_func=lambda i: f"{info_obat[i]['nama_obat']} (stok: {info_obat[i]['stok']} {info_obat[i]['satuan']})",
        key=f"obat_{keluhan_id}",
    )
    obat_dipakai = []
    for oid in pilih_obat:
        jml = st.number_input(
            f"Jumlah {info_obat[oid]['nama_obat']} ({info_obat[oid]['satuan']})",
            min_value=1, max_value=info_obat[oid]["stok"], value=1,
            key=f"jml_{keluhan_id}_{oid}",
        )
        obat_dipakai.append((oid, int(jml)))

    # ----- Rujukan -----
    st.markdown("**🏥 Rujukan**")
    rujuk = st.checkbox("Perlu dirujuk ke faskes mitra", key=f"rujuk_{keluhan_id}")
    faskes_id, alasan = None, ""
    if rujuk:
        faskes = run_query("SELECT id, nama, jenis FROM faskes_mitra ORDER BY nama")
        info_faskes = {f["id"]: f for f in faskes}
        faskes_id = st.selectbox(
            "Faskes tujuan",
            options=list(info_faskes.keys()),
            format_func=lambda i: f"{info_faskes[i]['nama']} ({info_faskes[i]['jenis']})",
            key=f"faskes_{keluhan_id}",
        )
        alasan = st.text_area("Alasan rujukan *", key=f"alasan_{keluhan_id}")

    if st.button("💾 Simpan Pelayanan", type="primary"):
        if not diagnosis.strip():
            st.error("Diagnosis awal wajib diisi.")
        elif rujuk and not alasan.strip():
            st.error("Alasan rujukan wajib diisi.")
        elif not obat_dipakai and not rujuk and not tindakan.strip():
            st.error("Isi tindakan, atau pilih obat, atau buat rujukan.")
        else:
            try:
                simpan_pelayanan(
                    keluhan_id, st.session_state["user_id"],
                    diagnosis.strip(), tindakan.strip(),
                    obat_dipakai, faskes_id, alasan.strip(),
                )
                st.session_state["pesan"] = f"Pelayanan untuk {k['nama']} tersimpan. Stok obat sudah diperbarui."
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menyimpan: {e}")


def riwayat():
    ui.section("Riwayat Pelayanan (100 terbaru)")
    data = run_query(
        """SELECT p.tanggal, k.kode, u.nama AS mahasiswa, p.diagnosis_awal AS diagnosis,
                  p.tindakan,
                  (SELECT GROUP_CONCAT(CONCAT(o.nama_obat, ' x', po.jumlah) SEPARATOR ', ')
                     FROM pelayanan_obat po JOIN obat o ON o.id = po.obat_id
                    WHERE po.pelayanan_id = p.id) AS obat,
                  (SELECT CONCAT(f.nama, ' (', r.status, ')')
                     FROM rujukan r JOIN faskes_mitra f ON f.id = r.faskes_id
                    WHERE r.pelayanan_id = p.id LIMIT 1) AS rujukan
           FROM pelayanan p
           JOIN keluhan k ON k.id = p.keluhan_id
           JOIN users u ON u.id = k.mahasiswa_id
           ORDER BY p.tanggal DESC LIMIT 100"""
    )
    if data:
        st.dataframe(pd.DataFrame(data), hide_index=True)
    else:
        st.info("Belum ada pelayanan.")


hitung = {r["status"]: r["n"] for r in run_query(
    "SELECT status, COUNT(*) AS n FROM keluhan GROUP BY status")}
ui.stats([("Menunggu", hitung.get("Menunggu", 0), "hourglass_top", "pink"),
          ("Dirujuk", hitung.get("Dirujuk", 0), "local_hospital", "purple"),
          ("Selesai", hitung.get("Selesai", 0), "check_circle", "green")])
st.write("")
tab1, tab2 = st.tabs(["🩺 Layani Pasien", "📋 Riwayat Pelayanan"])
with tab1:
    layani_pasien()
with tab2:
    riwayat()