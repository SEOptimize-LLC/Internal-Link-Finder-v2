import io
import zipfile
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

class ExportManager:
    def export_df(self, df: pd.DataFrame, filename: str = "export.csv"):
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download", data=csv_bytes, file_name=filename, mime="text/csv")

    def export_excel(self, sheets: dict, filename: str = "export.xlsx"):
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            for name, df in sheets.items():
                df.to_excel(writer, sheet_name=name[:31], index=False)
        st.download_button("Download", data=bio.getvalue(), file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def export_zip_csv(self, files: dict, filename: str = "bundle.zip"):
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fname, df in files.items():
                zf.writestr(fname, df.to_csv(index=False))
        st.download_button("Download", data=bio.getvalue(), file_name=filename, mime="application/zip")

    def _get_sheets_client(self):
        sheets_secrets = st.secrets.get("sheets", {})
        if not sheets_secrets:
            raise RuntimeError("Sheets secrets not configured.")
        creds = Credentials.from_service_account_info(sheets_secrets, scopes=SHEETS_SCOPES)
        gc = gspread.authorize(creds)
        return gc

    def export_to_google_sheets(self, sheets: dict, spreadsheet_title: str, create_new: bool = True) -> str:
        gc = self._get_sheets_client()
        if create_new:
            sh = gc.create(spreadsheet_title)
        else:
            sh = gc.open_by_key(spreadsheet_title)
        existing = {w.title: w for w in sh.worksheets()}
        for name, df in sheets.items():
            ws = existing.get(name)
            if ws:
                sh.del_worksheet(ws)
            ws = sh.add_worksheet(title=name[:100], rows=str(len(df)+10), cols=str(len(df.columns)+10))
            if len(df) == 0:
                ws.update("A1", [[c for c in df.columns]])
            else:
                values = [list(df.columns)] + df.astype(object).where(pd.notnull(df), "").values.tolist()
                ws.update("A1", values, value_input_option="RAW")
        return sh.url
