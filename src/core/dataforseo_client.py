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

    def _post(self, post_data: Dict) -> Dict:
        """Make POST request to DataForSEO API"""
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json"
        }
        try:
            resp = requests.post(
                self.BASE_URL,
                headers=headers,
                data=json.dumps(post_data),
                timeout=60
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            st.error(f"DataForSEO API request failed: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
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
        
        # Batch in groups of 1,000 (DataForSEO charges same for 1-1000)
        chunk_size = 1000
        
        # Map common location names to DataForSEO format
        location_name_map = {
            "US": "United States",
            "USA": "United States",
            "UK": "United Kingdom",
            "GB": "United Kingdom",
            "CA": "Canada",
            "AU": "Australia"
        }
        location_name = location_name_map.get(location, location)
        
        # Process keywords in chunks
        chunks = [keywords[i:i+chunk_size] for i in range(0, len(keywords), chunk_size)]
        
        for chunk_idx, chunk in enumerate(chunks):
            try:
                # Format exactly as shown in DataForSEO documentation
                # Using dict with numeric keys
                post_data = dict()
                post_data[0] = dict(
                    keywords=chunk,
                    location_name=location_name,
                    language_name=language
                )
                
                # Make API request
                response = self._post(post_data)
                
                # Parse response
                if response.get("status_code") == 20000:
                    tasks = response.get("tasks", [])
                    for task in tasks:
                        if task.get("status_code") == 20000:  # Task success
                            result_data = task.get("result", [])
                            for result in result_data:
                                items = result.get("items", [])
                                for item in items:
                                    kw = item.get("keyword", "")
                                    # DataForSEO returns search_volume directly
                                    vol = item.get("search_volume", 0) or 0
                                    if kw:
                                        # Store with lowercase for case-insensitive matching
                                        results[kw.lower()] = vol
                        else:
                            # Task-level error
                            error_msg = task.get("status_message", "Unknown error")
                            st.warning(f"DataForSEO task error for batch {chunk_idx+1}: {error_msg}")
                else:
                    # Response-level error
                    error_msg = response.get("status_message", "Unknown error")
                    st.error(f"DataForSEO response error: {error_msg}")
                
                # Rate limiting - be nice to the API
                if chunk_idx < len(chunks) - 1:
                    time.sleep(1)
                    
            except Exception as e:
                st.error(f"Error processing batch {chunk_idx+1} of {len(chunks)}: {str(e)}")
                continue
        
        # Show summary
        if results:
            st.info(f"📊 Successfully retrieved search volumes for {len(results)} keywords out of {len(keywords)} requested.")
        
        return results
