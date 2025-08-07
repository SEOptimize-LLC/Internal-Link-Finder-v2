import base64
import json
import time
from typing import List, Dict
import requests
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class DataForSEOClient:
    BASE_URL = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"

    def __init__(self):
        s = st.secrets.get("dataforseo", {})
        self.login = s.get("login")
        self.password = s.get("password")
        self.default_location = s.get("default_location", "US")
        self.default_language = s.get("default_language", "English")
        if not (self.login and self.password):
            raise RuntimeError("DataForSEO credentials not configured in secrets.")
        auth_str = f"{self.login}:{self.password}"
        self.auth_header = "Basic " + base64.b64encode(auth_str.encode()).decode()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10),
           retry=retry_if_exception_type((requests.RequestException,)))
    def _post(self, payload: Dict) -> Dict:
        headers = {"Authorization": self.auth_header, "Content-Type": "application/json"}
        resp = requests.post(self.BASE_URL, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        return resp.json()

    @st.cache_data(show_spinner=False)
    def get_monthly_search_volume(self, keywords: List[str], location: str = "US", language: str = "English") -> Dict[str, int]:
        if not keywords:
            return {}
        results: Dict[str, int] = {}
        chunk_size = 500
        loc_code = {"US": 2840, "United States": 2840, "GB": 2826, "UK": 2826, "Canada": 2124}.get(location, 2840)
        chunks = [keywords[i:i+chunk_size] for i in range(0, len(keywords), chunk_size)]
        for chunk in chunks:
            payload = {
                "data": [
                    {
                        "keywords": chunk,
                        "location_code": loc_code,
                        "language_name": language
                    }
                ]
            }
            data = self._post(payload)
            tasks = data.get("tasks", [])
            for t in tasks:
                for block in t.get("result", []):
                    for item in block.get("items", []):
                        kw = item.get("keyword", "")
                        ms = item.get("monthly_searches", [])
                        vol = 0
                        if ms:
                            vol = ms[-1].get("search_volume", 0) or 0
                        else:
                            vol = item.get("search_volume", 0) or 0
                        if kw:
                            results[kw] = vol
            time.sleep(1)
        return results
