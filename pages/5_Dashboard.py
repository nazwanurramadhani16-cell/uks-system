import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from db.connection import run_query
from utils.auth import require_role
from utils import ui

ui.setup("Dashboard", "📊", roles=["admin", "petugas"])
require_role("admin", "petugas")

ui.header("Dashboard UKS", "Pantau pola keluhan, pemakaian obat, dan rujukan dalam satu layar.")

MIN_BULAN = 3  # minimal bulan penuh data pemakaian agar prediksi ditampilkan
HARI = ui.HARI


def muat(query, kolom, kolom_tanggal=None):
    df = pd.DataFrame(run_query(query), columns=kolom)
    if kolom_tanggal and not df.empty:
        df[kolom_tanggal] = pd.to_datetime(df[kolom_tanggal])
    return df


# ---------------------------------------------------------------- DATA
keluhan = muat("SELECT tanggal, keluhan_utama, tingkat_nyeri, status FROM keluhan",
               ["tanggal", "keluhan_utama", "tingkat_nyeri", "status"], "tanggal")
pelayanan = muat("SELECT tanggal FROM pelayanan", ["tanggal"], "tanggal")
pakai = muat(
    """SELECT p.tanggal, o.nama_obat, po.jumlah
       FROM pelayanan_obat po
       JOIN pelayanan p ON p.id = po.pelayanan_id
       JOIN obat o ON o.id = po.obat_id""",
    ["tanggal", "nama_obat", "jumlah"], "tanggal")
rujukan = muat(
    """SELECT r.created_at, r.status, f.nama AS faskes
       FROM rujukan r JOIN faskes_mitra f ON f.id = r.faskes_id""",
    ["created_at", "status", "faskes"], "created_at")
stok = muat("SELECT nama_obat, satuan, stok, stok_minimum FROM obat ORDER BY nama_obat",
            ["nama_obat", "satuan", "stok", "stok_minimum"])

# ------------------------------------------------------------- FILTER
PERIODE = {"30 hari": 30, "90 hari": 90, "6 bulan": 180, "Semua data": None}
pilih = st.segmented_control("Periode", list(PERIODE.keys()), default="Semua data",
                             selection_mode="single", key="periode")
pilih = pilih or "Semua data"
hari = PERIODE[pilih]
sekarang = pd.Timestamp.now()
batas = None if hari is None else sekarang - pd.Timedelta(days=hari)
batas_lalu = None if hari is None else sekarang - pd.Timedelta(days=2 * hari)


def saring(df, kolom):
    if batas is None or df.empty:
        return df
    return df[df[kolom] >= batas]


def sebelumnya(df, kolom):
    """data pada periode yang sama persis sebelum periode terpilih"""
    if batas is None or df.empty:
        return None
    return df[(df[kolom] >= batas_lalu) & (df[kolom] < batas)]


def delta(now, prev):
    if prev is None or prev == 0:
        return ""
    p = round((now - prev) / prev * 100)
    return f"{'naik' if p > 0 else 'turun' if p < 0 else 'tetap'} {abs(p)}% dari periode lalu" if p else "sama dengan periode lalu"


k = saring(keluhan, "tanggal")
pl = saring(pelayanan, "tanggal")
pk = saring(pakai, "tanggal")
rj = saring(rujukan, "created_at")
kp, pp = sebelumnya(keluhan, "tanggal"), sebelumnya(pelayanan, "tanggal")
rp = sebelumnya(rujukan, "created_at")

# ------------------------------------------------------------ RINGKASAN
ui.stats([
    ("Keluhan masuk", len(k), "assignment", "purple", delta(len(k), None if kp is None else len(kp))),
    ("Pelayanan", len(pl), "stethoscope", "blue", delta(len(pl), None if pp is None else len(pp))),
    ("Rujukan", len(rj), "local_hospital", "pink", delta(len(rj), None if rp is None else len(rp))),
    ("Obat keluar (unit)", int(pk["jumlah"].sum()) if not pk.empty else 0, "medication", "green"),
    ("Rata-rata nyeri", f"{k['tingkat_nyeri'].mean():.1f}/10" if not k.empty else "-", "ecg_heart", "teal"),
])

st.write("")
tab_pola, tab_obat, tab_rujuk, tab_prediksi = st.tabs(
    ["🩺 Pola Keluhan", "💊 Obat & Stok", "🏥 Rujukan", "🔮 Prediksi Kebutuhan Obat"])

# --------------------------------------------------------- POLA KELUHAN
with tab_pola:
    if k.empty:
        ui.rows([], "Belum ada data keluhan pada periode ini.")
    else:
        per_hari = k["tanggal"].dt.dayofweek.value_counts().reindex(range(7), fill_value=0)
        per_jam = k["tanggal"].dt.hour.value_counts().reindex(range(24), fill_value=0)
        top1 = k["keluhan_utama"].str.strip().str.lower().value_counts()
        c1, c2, c3 = st.columns(3, gap="large")
        with c1, ui.card():
            ui.insight("event", "purple", HARI[int(per_hari.idxmax())], "hari paling ramai")
        with c2, ui.card():
            ui.insight("schedule", "pink", f"Pukul {int(per_jam.idxmax()):02d}.00", "jam paling ramai")
        with c3, ui.card():
            ui.insight("sick", "green", top1.index[0].capitalize(), f"keluhan terbanyak ({int(top1.iloc[0])}x)")

        kiri, kanan = st.columns([2, 1], gap="large")
        with kiri:
            ui.section("Tren keluhan per bulan")
            with ui.card():
                bln = (k.groupby(k["tanggal"].dt.to_period("M").astype(str)).size().reset_index())
                bln.columns = ["bulan", "jumlah"]
                fig = px.area(bln, x="bulan", y="jumlah", markers=True, color_discrete_sequence=[ui.PURPLE])
                fig.update_traces(line_shape="spline", fillcolor="rgba(124,102,214,.15)")
                ui.plot(fig, h=280)
        with kanan:
            ui.section("Status keluhan")
            with ui.card():
                st_k = k["status"].value_counts().rename_axis("status").reset_index(name="jumlah")
                warna = {"Menunggu": ui.PINK, "Dilayani": ui.BLUE, "Dirujuk": ui.PURPLE, "Selesai": ui.GREEN}
                fig = px.pie(st_k, names="status", values="jumlah", hole=.62,
                             color="status", color_discrete_map=warna)
                fig.update_traces(textinfo="value", marker_line_color="#fff", marker_line_width=3)
                ui.plot(fig, h=280, legend=True)

        kiri, kanan = st.columns(2, gap="large")
        with kiri:
            ui.section("Keluhan terbanyak")
            with ui.card():
                top = top1.head(8).rename_axis("keluhan").reset_index(name="jumlah")
                fig = px.bar(top, x="jumlah", y="keluhan", orientation="h", color_discrete_sequence=[ui.PINK])
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                ui.plot(fig, h=300)
        with kanan:
            ui.section("Sebaran tingkat nyeri")
            with ui.card():
                ny = k["tingkat_nyeri"].value_counts().reindex(range(11), fill_value=0).reset_index()
                ny.columns = ["nyeri", "jumlah"]
                ny["kelompok"] = ny["nyeri"].map(lambda n: "Berat (7-10)" if n >= 7 else "Sedang (4-6)" if n >= 4 else "Ringan (0-3)")
                fig = px.bar(ny, x="nyeri", y="jumlah", color="kelompok",
                             color_discrete_map={"Ringan (0-3)": ui.GREEN, "Sedang (4-6)": ui.BLUE, "Berat (7-10)": ui.PINK})
                fig.update_xaxes(dtick=1)
                ui.plot(fig, h=300, legend=True)

        ui.section("Kapan UKS paling ramai", "makin pekat = makin banyak keluhan")
        with ui.card():
            pivot = (k.assign(h=k["tanggal"].dt.dayofweek, j=k["tanggal"].dt.hour)
                     .groupby(["h", "j"]).size().unstack(fill_value=0)
                     .reindex(index=range(7), columns=range(24), fill_value=0))
            fig = go.Figure(go.Heatmap(
                z=pivot.values, x=[f"{j:02d}" for j in range(24)], y=HARI, xgap=3, ygap=3,
                colorscale=[[0, "#F1F0FB"], [.5, "#B9A6F0"], [1, "#6A55C9"]], showscale=False,
                hovertemplate="%{y}, pukul %{x}.00<br>%{z} keluhan<extra></extra>"))
            fig.update_yaxes(autorange="reversed")
            ui.plot(fig, h=290)
        st.caption("Keluhan utama berupa teks bebas, jadi tulisan yang berbeda dihitung terpisah "
                   "(misal 'sakit kepala' dan 'pusing'). Bisa dirapikan dengan pilihan baku di form.")

# ----------------------------------------------------------- OBAT & STOK
with tab_obat:
    kiri, kanan = st.columns(2, gap="large")
    with kiri:
        ui.section("Obat paling sering dipakai")
        if pk.empty:
            ui.rows([], "Belum ada pemakaian obat pada periode ini.")
        else:
            with ui.card():
                top_obat = (pk.groupby("nama_obat")["jumlah"].sum()
                            .sort_values(ascending=False).head(10).reset_index())
                fig = px.bar(top_obat, x="jumlah", y="nama_obat", orientation="h", color_discrete_sequence=[ui.GREEN])
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                ui.plot(fig, h=340)
    with kanan:
        ui.section("Stok saat ini", "bar pink = di bawah batas minimum")
        if stok.empty:
            ui.rows([], "Belum ada data obat.")
        else:
            with ui.card():
                ui.stock_bars(stok.assign(r=stok["stok"] / stok["stok_minimum"].clip(lower=1))
                              .sort_values("r").drop(columns="r"))

    if not stok.empty:
        menipis = stok[stok["stok"] <= stok["stok_minimum"]]
        if len(menipis):
            st.warning("Stok menipis: " + ", ".join(menipis["nama_obat"]))
        else:
            st.success("Semua stok obat di atas batas minimum.")

# --------------------------------------------------------------- RUJUKAN
with tab_rujuk:
    if rj.empty:
        ui.rows([], "Belum ada rujukan pada periode ini.")
    else:
        kiri, kanan = st.columns(2, gap="large")
        with kiri:
            ui.section("Rujukan per faskes")
            with ui.card():
                per_f = rj["faskes"].value_counts().rename_axis("faskes").reset_index(name="jumlah")
                ui.plot(px.bar(per_f, x="faskes", y="jumlah", color_discrete_sequence=[ui.BLUE]), h=300)
        with kanan:
            ui.section("Status tindak lanjut")
            with ui.card():
                per_s = rj["status"].value_counts().rename_axis("status").reset_index(name="jumlah")
                warna = {"Dibuat": ui.PINK, "Diterima": ui.BLUE, "Ditangani": ui.PURPLE, "Selesai": ui.GREEN}
                fig = px.pie(per_s, names="status", values="jumlah", hole=.62, color="status", color_discrete_map=warna)
                fig.update_traces(textinfo="value", marker_line_color="#fff", marker_line_width=3)
                ui.plot(fig, h=300, legend=True)

# ------------------------------------------------------------- PREDIKSI
with tab_prediksi:
    ui.section("Prediksi kebutuhan obat 1 bulan ke depan")
    st.caption(
        f"Metode: rata-rata bergerak (moving average) dari 3 bulan penuh terakhir. "
        f"Prediksi hanya ditampilkan jika obat punya minimal {MIN_BULAN} bulan data pemakaian, "
        f"supaya sistem tidak menebak dari data yang terlalu sedikit. "
        f"Bulan berjalan tidak dipakai karena datanya belum lengkap.")

    bulan_ini = pd.Period(pd.Timestamp.now(), freq="M")
    stok_map = dict(zip(stok["nama_obat"], stok["stok"]))
    hasil, riwayat, kurang_data = [], {}, []

    if not pakai.empty:
        p = pakai.copy()
        p["bulan"] = p["tanggal"].dt.to_period("M")
        p = p[p["bulan"] < bulan_ini]  # hanya bulan penuh

        for nama in pakai["nama_obat"].unique():
            g = p[p["nama_obat"] == nama]
            if g.empty:
                kurang_data.append(nama)
                continue
            per_bulan = g.groupby("bulan")["jumlah"].sum()
            rentang = pd.period_range(per_bulan.index.min(), bulan_ini - 1, freq="M")
            seri = per_bulan.reindex(rentang, fill_value=0)
            if len(seri) < MIN_BULAN:
                kurang_data.append(nama)
                continue
            rata = seri.tail(3).mean()
            prediksi = math.ceil(rata)
            sekarang_stok = int(stok_map.get(nama, 0))
            riwayat[nama] = seri
            hasil.append({
                "Obat": nama,
                "Data (bulan)": len(seri),
                "Rata-rata 3 bln": round(rata, 1),
                "Prediksi kebutuhan": prediksi,
                "Stok saat ini": sekarang_stok,
                "Perlu tambah": max(0, prediksi - sekarang_stok),
                "Status": "⚠️ Berisiko kurang" if sekarang_stok < prediksi else "✅ Cukup",
            })

    if not hasil:
        with ui.card():
            ui.rows([], f"Data belum cukup untuk membuat prediksi. Dibutuhkan minimal {MIN_BULAN} "
                        "bulan penuh data pemakaian obat. Prediksi muncul otomatis setelah data terkumpul.")
    else:
        df_h = pd.DataFrame(hasil).sort_values("Perlu tambah", ascending=False)
        berisiko = int((df_h["Status"] != "✅ Cukup").sum())
        ui.stats([("Obat diprediksi", len(df_h), "insights", "purple"),
                  ("Berisiko kurang", berisiko, "warning", "pink"),
                  ("Total perlu ditambah (unit)", int(df_h["Perlu tambah"].sum()), "inventory_2", "blue")])
        st.write("")
        if berisiko:
            st.warning(f"{berisiko} obat diperkirakan kurang untuk bulan depan.")
        else:
            st.success("Semua obat yang bisa diprediksi diperkirakan cukup untuk bulan depan.")
        st.dataframe(df_h, hide_index=True)

        pilih_obat = st.selectbox("Lihat grafik pemakaian obat", list(riwayat.keys()))
        seri = riwayat[pilih_obat]
        df_g = pd.DataFrame({"bulan": seri.index.astype(str), "jumlah": seri.values, "jenis": "Aktual"})
        pred = [h for h in hasil if h["Obat"] == pilih_obat][0]["Prediksi kebutuhan"]
        df_g = pd.concat([df_g, pd.DataFrame({"bulan": [str(bulan_ini)], "jumlah": [pred], "jenis": ["Prediksi"]})])
        with ui.card():
            ui.plot(px.bar(df_g, x="bulan", y="jumlah", color="jenis",
                           color_discrete_map={"Aktual": ui.PURPLE, "Prediksi": ui.PINK}),
                    h=300, legend=True)

    if kurang_data:
        st.caption("Belum cukup data untuk: " + ", ".join(sorted(kurang_data)))
