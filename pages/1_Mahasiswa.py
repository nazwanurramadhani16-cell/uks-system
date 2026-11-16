import random
import string
import streamlit as st
from db.connection import run_query
from utils import ui
from utils.auth import require_role

ui.setup("Form Keluhan", "🧑‍🎓", roles=["mahasiswa"], narrow=True)
require_role("mahasiswa")

ui.header("Form keluhan", "Isi keluhanmu sebelum datang ke UKS, lalu tunjukkan kodenya ke petugas.")

GEJALA = ["Demam", "Batuk", "Pilek", "Sakit kepala", "Mual", "Muntah",
          "Diare", "Nyeri perut", "Pusing", "Lemas", "Ruam kulit", "Luka"]

with st.form("form_keluhan", clear_on_submit=True):
    keluhan_utama = st.text_input("Keluhan utama *", placeholder="Contoh: sakit kepala")
    lama = st.selectbox("Sudah berapa lama?",
                        ["Kurang dari 1 hari", "1-3 hari", "4-7 hari", "Lebih dari 1 minggu"])
    nyeri = st.slider("Tingkat nyeri (0 = tidak nyeri, 10 = sangat nyeri)", 0, 10, 0)
    gejala = st.multiselect("Gejala lain", GEJALA)
    alergi = st.text_area("Riwayat alergi obat/makanan", placeholder="Kosongkan jika tidak ada")
    kirim = st.form_submit_button("Kirim Keluhan")

if kirim:
    if not keluhan_utama.strip():
        st.error("Keluhan utama wajib diisi.")
    else:
        kode = "UKS-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        run_query(
            """INSERT INTO keluhan
               (kode, mahasiswa_id, keluhan_utama, lama_keluhan, tingkat_nyeri, gejala_lain, riwayat_alergi)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (kode, st.session_state["user_id"], keluhan_utama.strip(), lama, nyeri,
             ", ".join(gejala), alergi.strip() or "Tidak ada"),
            fetch=False,
        )
        st.session_state["kode_terakhir"] = kode
        st.rerun()

# ---------- Rangkuman keluhan terakhir ----------
if "kode_terakhir" in st.session_state:
    k = run_query(
        """SELECT k.*, m.nim FROM keluhan k
           JOIN mahasiswa m ON m.user_id = k.mahasiswa_id
           WHERE k.kode = %s""",
        (st.session_state["kode_terakhir"],),
    )[0]

    ringkasan = (
        f"RANGKUMAN KELUHAN\n"
        f"Kode      : {k['kode']}\n"
        f"Nama      : {st.session_state['nama']}\n"
        f"NIM       : {k['nim']}\n"
        f"Tanggal   : {k['tanggal']:%d-%m-%Y %H:%M}\n"
        f"Keluhan   : {k['keluhan_utama']}\n"
        f"Lama      : {k['lama_keluhan']}\n"
        f"Nyeri     : {k['tingkat_nyeri']}/10\n"
        f"Gejala    : {k['gejala_lain'] or '-'}\n"
        f"Alergi    : {k['riwayat_alergi']}\n"
    )

    st.success("Keluhan terkirim! Tunjukkan kode ini ke petugas UKS 👇")
    st.code(k["kode"])
    st.text(ringkasan)
    st.download_button("⬇️ Unduh Rangkuman", ringkasan, file_name=f"keluhan_{k['kode']}.txt")

# ---------- Riwayat ----------
ui.section("Riwayat keluhanku")
riwayat = run_query(
    """SELECT kode, tanggal, keluhan_utama, status FROM keluhan
       WHERE mahasiswa_id = %s ORDER BY tanggal DESC""",
    (st.session_state["user_id"],),
)
if riwayat:
    ui.rows([("sick", ui.STATUS_TONE.get(r["status"], "teal"), r["keluhan_utama"],
              f"{r['kode']} · {r['tanggal']:%d-%m-%Y %H:%M}", r["status"],
              ui.STATUS_TONE.get(r["status"], "teal")) for r in riwayat])
else:
    st.info("Belum ada keluhan.")