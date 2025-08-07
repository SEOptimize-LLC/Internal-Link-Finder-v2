import base64
import json
import time
from typing import List, Dict
import requests
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class DataForSEOClient:
    # Updated to use clickstream endpoint as requested
    BASE_URL = "https://api.dataforseo.com/v3/keywords_data/clickstream_data/dataforseo_search_volume/live"

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

    def get_monthly_search_volume(self, keywords: List[str], location: str = "US", language: str = "English") -> Dict[str, int]:
        """
        Get monthly search volumes for keywords using DataForSEO clickstream endpoint.
        Batches keywords in groups of 1,000 for cost efficiency.
        """
        if not keywords:
            return {}
        
        results: Dict[str, int] = {}
        
        # Batch in groups of 1,000 as requested (DataForSEO charges same for 1 or 1000)
        chunk_size = 1000
        
        # Location codes mapping
        loc_code = {
            "US": 2840, 
            "United States": 2840, 
            "GB": 2826, 
            "UK": 2826, 
            "Canada": 2124,
            "AU": 2036,
            "Australia": 2036
        }.get(location, 2840)
        
        # Process keywords in chunks
        chunks = [keywords[i:i+chunk_size] for i in range(0, len(keywords), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            try:
                # Prepare payload for clickstream endpoint
                payload = {
                    "data": [
                        {
                            "keywords": chunk,
                            "location_code": loc_code,
                            "language_code": "en" if language == "English" else language.lower()[:2]
                        }
                    ]
                }
                
                # Make API request
                data = self._post(payload)
                
                # Parse response
                tasks = data.get("tasks", [])
                for task in tasks:
                    if task.get("status_code") == 20000:  # Success
                        for result in task.get("result", []):
                            for item in result.get("items", []):
                                kw = item.get("keyword", "")
                                # For clickstream endpoint, volume is directly in search_volume field
                                vol = item.get("search_volume", 0) or 0
                                if kw:
                                    results[kw.lower()] = vol
                    else:
                        # Log error but continue processing
                        error_msg = task.get("status_message", "Unknown error")
                        st.warning(f"DataForSEO API error for batch {i+1}: {error_msg}")
                
                # Rate limiting - be nice to the API
                if i < len(chunks) - 1:
                    time.sleep(1)
                    
            except Exception as e:
                st.error(f"Error processing batch {i+1} of {len(chunks)}: {str(e)}")
                continue
        
        return results


# Standalone cached function to avoid hashing issues
@st.cache_data(show_spinner=False, ttl=3600)  # Cache for 1 hour
def get_search_volumes_cached(keywords: List[str], login: str, password: str, location: str = "US", language: str = "English") -> Dict[str, int]:
    """
    Cached wrapper for DataForSEO API calls.
    Cache key includes keywords and credentials to ensure proper caching.
    """
    client = DataForSEOClient()
    return client.get_monthly_search_volume(keywords, location, language)
