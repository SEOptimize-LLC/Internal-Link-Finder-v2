import streamlit as st

def render_upload_section():
    c1, c2, c3 = st.columns(3)
    with c1:
        links = st.file_uploader(
            "Screaming Frog Internal Links", 
            type=["csv", "xlsx", "xls"], 
            key="links_file",
            help="Upload CSV or Excel file"
        )
    with c2:
        embeddings = st.file_uploader(
            "Embeddings File", 
            type=["csv", "xlsx", "xls"], 
            key="embeddings_file",
            help="Upload CSV or Excel file"
        )
    with c3:
        gsc = st.file_uploader(
            "GSC Data (optional)", 
            type=["csv", "xlsx", "xls"], 
            key="gsc_file",
            help="Upload CSV or Excel file"
        )
    return {"links": links, "embeddings": embeddings, "gsc": gsc}

def render_analysis_controls():
    st.subheader("Parameters")
    top_k_related = st.slider("Top related URLs per page", min_value=5, max_value=20, value=10, step=1)
    return {"top_k_related": top_k_related}
