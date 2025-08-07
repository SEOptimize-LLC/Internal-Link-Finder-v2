import io
import zipfile
import pandas as pd
import streamlit as st

class ExportManager:
    """Simplified export manager without Google Sheets integration"""
    
    def export_df(self, df: pd.DataFrame, filename: str = "export.csv"):
        """Export DataFrame as CSV with download button"""
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download CSV",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            use_container_width=True
        )

    def export_excel(self, sheets: dict, filename: str = "export.xlsx"):
        """Export multiple DataFrames as Excel with multiple sheets"""
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            for name, df in sheets.items():
                # Excel sheet names are limited to 31 characters
                sheet_name = name[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        excel_bytes = bio.getvalue()
        st.download_button(
            label="📥 Download Excel",
            data=excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    def export_zip_csv(self, files: dict, filename: str = "bundle.zip"):
        """Export multiple DataFrames as CSV files in a ZIP archive"""
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fname, df in files.items():
                csv_data = df.to_csv(index=False)
                zf.writestr(fname, csv_data)
        
        zip_bytes = bio.getvalue()
        st.download_button(
            label="📥 Download ZIP Bundle",
            data=zip_bytes,
            file_name=filename,
            mime="application/zip",
            use_container_width=True
        )
