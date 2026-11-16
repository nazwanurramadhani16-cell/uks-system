import bcrypt
import streamlit as st
from db.connection import run_query


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())


def login(email, password):
    rows = run_query("SELECT * FROM users WHERE email = %s", (email,))
    if rows and verify_password(password, rows[0]["password_hash"]):
        return rows[0]
    return None


def require_role(*roles):
    """Taruh di paling atas tiap halaman untuk membatasi akses."""
    if st.session_state.get("role") not in roles:
        st.error("Kamu tidak punya akses ke halaman ini.")
        st.stop()