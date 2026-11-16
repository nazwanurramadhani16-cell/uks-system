import streamlit as st
import mysql.connector


def get_connection():
    cfg = st.secrets["mysql"]
    opts = dict(
        host=cfg["host"],
        port=int(cfg["port"]),
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        use_pure=True,
        connection_timeout=15,
    )
    # opsional: verifikasi sertifikat TLS. Kosongkan saja kalau tidak dipakai.
    if cfg.get("ssl_ca"):
        opts.update(ssl_ca=cfg["ssl_ca"], ssl_verify_cert=True, ssl_verify_identity=True)
    return mysql.connector.connect(**opts)


def run_query(query, params=None, fetch=True):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(query, params or ())
        if fetch:
            return cur.fetchall()
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()