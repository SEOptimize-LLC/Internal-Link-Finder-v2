import pandas as pd
import streamlit as st
from typing import Dict, List
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

@st.cache_data(show_spinner=False)
def _cached_gsc_query(creds_info: dict, domain_property: str, start_date: str, end_date: str):
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    service = build("webmasters", "v3", credentials=creds)
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["page","query"],
        "rowLimit": 25000
    }
    response = service.searchanalytics().query(siteUrl=domain_property, body=body).execute()
    rows = response.get("rows", [])
    data = []
    for r in rows:
        keys = r.get("keys", [])
        page = keys[0] if len(keys) > 0 else ""
        query = keys[1] if len(keys) > 1 else ""
        data.append({
            "date": None,
            "page": page,
            "query": query,
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": float(r.get("ctr", 0.0)),
            "position": float(r.get("position", 0.0))
        })
    return pd.DataFrame(data)

class GSCDataProcessor:
    def __init__(self):
        pass

    def fetch_gsc_api(self, domain_property: str, date_range: str = "Last 90 days") -> pd.DataFrame:
        gsc_secrets = st.secrets.get("gsc", {})
        if not gsc_secrets:
            raise RuntimeError("GSC secrets not configured.")
        from datetime import date, timedelta
        end_date = date.today() - timedelta(days=3)
        if date_range == "Last 28 days":
            start_date = end_date - timedelta(days=28)
        elif date_range == "Last 180 days":
            start_date = end_date - timedelta(days=180)
        else:
            start_date = end_date - timedelta(days=90)
        return _cached_gsc_query(gsc_secrets, domain_property, start_date.isoformat(), end_date.isoformat())

    def calculate_url_metrics(self, gsc_data: pd.DataFrame) -> pd.DataFrame:
        if gsc_data is None or gsc_data.empty:
            return pd.DataFrame(columns=["page","url_queries_count","url_clicks","url_impressions"])
        agg = gsc_data.groupby("page", as_index=False).agg(
            url_queries_count=("query","nunique"),
            url_clicks=("clicks","sum"),
            url_impressions=("impressions","sum")
        )
        return agg

    def extract_top_keywords_by_url(self, gsc_data: pd.DataFrame, top_n: int = 3) -> Dict[str, List[str]]:
        if gsc_data is None or gsc_data.empty:
            return {}
        gsc_data = gsc_data.copy()
        gsc_data["rank"] = gsc_data.groupby("page")["clicks"].rank("dense", ascending=False)
        top_clicks = gsc_data[gsc_data["rank"] <= top_n]
        if top_clicks.empty:
            gsc_data["rank"] = gsc_data.groupby("page")["impressions"].rank("dense", ascending=False)
            top_clicks = gsc_data[gsc_data["rank"] <= top_n]
        out: Dict[str, List[str]] = {}
        for page, sub in top_clicks.groupby("page"):
            out[page] = [q for q in sub["query"].dropna().astype(str).tolist() if q]
        return out
