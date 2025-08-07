import streamlit as st

def render_status_badge(label: str, status: str):
    color = "green" if status == "OK" else "red"
    st.sidebar.markdown(f"- {label}: :{color}[{status}]")

def render_info_box(text: str):
    st.info(text)

def render_warning_box(text: str):
    st.warning(text)
