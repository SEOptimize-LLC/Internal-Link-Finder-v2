import base64
import json
import time
from typing import List, Dict
import requests
import streamlit as st

class DataForSEOClient:
    # Using the correct endpoint
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

    def _post(self, payload: List[Dict]) -> Dict:
        """Make POST request to DataForSEO API"""
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json"
        }
        try:
            resp = requests.post(
                self.BASE_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=60
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            st.error(f"DataForSEO API request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                st.error(f"Response: {e.response.text}")
            raise

    def get_monthly_search_volume(self, keywords: List[str], location: str = "US", language: str = "English") -> Dict[str, int]:
        """
        Get monthly search volumes for keywords using DataForSEO clickstream endpoint.
        Batches keywords in groups of 1,000 for cost efficiency.
        """
        if not keywords:
            return {}
        
        results: Dict[str, int] = {}
        
        # Batch in groups of 1,000 as requested
        chunk_size = 1000
        
        # Location codes mapping - DataForSEO uses specific location codes
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
                # Correct payload format for clickstream endpoint
                # The API expects an array of task objects
                payload = [
                    {
                        "keywords": chunk,
                        "location_code": loc_code,
                        "language_code": "en"  # DataForSEO uses language codes, not names
                    }
                ]
                
                # Make API request
                data = self._post(payload)
                
                # Parse response
                if "tasks" in data:
                    for task in data["tasks"]:
                        if task.get("status_code") == 20000:  # Success
                            result_data = task.get("result", [])
                            if result_data and len(result_data) > 0:
                                items = result_data[0].get("items", [])
                                for item in items:
                                    kw = item.get("keyword", "")
                                    vol = item.get("search_volume", 0)
                                    if kw:
                                        # Store with lowercase for case-insensitive matching
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


# Standalone function to avoid caching the client instance
def get_search_volumes(keywords: List[str], login: str, password: str, location: str = "US") -> Dict[str, int]:
    """Non-cached version for direct use"""
    # Create a temporary client just for this request
    temp_secrets = st.secrets._store.copy()
    temp_secrets["dataforseo"] = {"login": login, "password": password}
    
    # Temporarily override secrets
    original_secrets = st.secrets._store
    st.secrets._store = temp_secrets
    
    try:
        client = DataForSEOClient()
        return client.get_monthly_search_volume(keywords, location, "English")
    finally:
        # Restore original secrets
        st.secrets._store = original_secrets
