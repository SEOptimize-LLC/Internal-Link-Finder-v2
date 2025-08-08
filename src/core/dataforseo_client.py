import base64
import json
import time
from typing import List, Dict
import requests
import streamlit as st

class DataForSEOClient:
    # Using the clickstream endpoint as specified
    BASE_URL = "https://api.dataforseo.com/v3/keywords_data/clickstream_data/dataforseo_search_volume/live"
    
    # DataForSEO API limits from documentation
    MAX_KEYWORD_LENGTH = 200  # Maximum characters per keyword
    MAX_KEYWORDS_PER_REQUEST = 1000  # Maximum keywords per API request
    MIN_KEYWORD_LENGTH = 1  # Minimum characters per keyword

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
                error_text = e.response.text[:500]  # Show first 500 chars of error
                st.error(f"Response: {error_text}")
            raise

    def _clean_keyword(self, keyword: str) -> str:
        """Clean and validate a keyword according to DataForSEO requirements"""
        # Remove extra whitespace
        keyword = ' '.join(keyword.split())
        
        # Remove quotes and other problematic characters
        keyword = keyword.replace('"', '').replace("'", '').replace('\n', ' ').replace('\r', ' ')
        
        # Trim to max length if needed
        if len(keyword) > self.MAX_KEYWORD_LENGTH:
            # Try to cut at a word boundary
            keyword = keyword[:self.MAX_KEYWORD_LENGTH].rsplit(' ', 1)[0]
        
        return keyword.strip()

    def get_monthly_search_volume(self, keywords: List[str], location: str = "US", language: str = "English") -> Dict[str, int]:
        """
        Get monthly search volumes for keywords using DataForSEO clickstream endpoint.
        Batches keywords in groups of 1,000 for cost efficiency.
        Cleans and validates keywords before sending.
        """
        if not keywords:
            return {}
        
        # Clean and validate keywords
        valid_keywords = []
        skipped_keywords = []
        keyword_mapping = {}  # Map cleaned keywords back to originals
        
        for original_kw in keywords:
            cleaned_kw = self._clean_keyword(original_kw)
            
            # Validate length
            if self.MIN_KEYWORD_LENGTH <= len(cleaned_kw) <= self.MAX_KEYWORD_LENGTH:
                valid_keywords.append(cleaned_kw)
                # Store mapping for result retrieval
                keyword_mapping[cleaned_kw.lower()] = original_kw.lower()
            else:
                skipped_keywords.append((original_kw, f"Length: {len(cleaned_kw)}"))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in valid_keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)
        
        # Report skipped keywords if any
        if skipped_keywords:
            st.warning(f"⚠️ Skipped {len(skipped_keywords)} problematic keywords")
            with st.expander(f"View skipped keywords ({len(skipped_keywords)})"):
                for kw, reason in skipped_keywords[:10]:  # Show first 10
                    st.write(f"• {kw[:80]}... - {reason}")
                if len(skipped_keywords) > 10:
                    st.write(f"... and {len(skipped_keywords) - 10} more")
        
        if not unique_keywords:
            st.warning("No valid keywords to process after cleaning and filtering")
            return {}
        
        st.info(f"📊 Processing {len(unique_keywords)} unique keywords (from {len(keywords)} original)")
        
        results: Dict[str, int] = {}
        
        # Map location names to DataForSEO format
        location_name_map = {
            "US": "United States",
            "USA": "United States",
            "UK": "United Kingdom",
            "GB": "United Kingdom",
            "CA": "Canada",
            "AU": "Australia",
            "DE": "Germany",
            "FR": "France",
            "ES": "Spain",
            "IT": "Italy",
            "JP": "Japan",
            "IN": "India"
        }
        location_name = location_name_map.get(location, location)
        
        # Process keywords in chunks
        chunks = [unique_keywords[i:i+self.MAX_KEYWORDS_PER_REQUEST] 
                 for i in range(0, len(unique_keywords), self.MAX_KEYWORDS_PER_REQUEST)]
        
        successful_batches = 0
        failed_batches = 0
        total_volumes_retrieved = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for chunk_idx, chunk in enumerate(chunks):
            try:
                # Update progress
                progress = (chunk_idx + 1) / len(chunks)
                progress_bar.progress(progress)
                status_text.text(f"Processing batch {chunk_idx + 1} of {len(chunks)}...")
                
                # Format payload according to DataForSEO documentation
                post_data = dict()
                post_data[0] = dict(
                    keywords=chunk,
                    location_name=location_name,
                    language_name=language,
                    include_clickstream_data=False,  # Set to True if you want additional clickstream metrics
                    date_from="2024-01-01",  # Optional: specify date range
                    search_partners=False  # Include search partners data
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
                                    vol = item.get("search_volume", 0) or 0
                                    
                                    if kw:
                                        kw_lower = kw.lower()
                                        results[kw_lower] = vol
                                        
                                        # Also store with original keyword if we have mapping
                                        if kw_lower in keyword_mapping:
                                            results[keyword_mapping[kw_lower]] = vol
                                        
                                        total_volumes_retrieved += 1
                            
                            successful_batches += 1
                        else:
                            # Task-level error
                            error_msg = task.get("status_message", "Unknown error")
                            error_path = task.get("path", ["Unknown"])
                            st.warning(f"Batch {chunk_idx+1} error: {error_msg} (Path: {error_path})")
                            failed_batches += 1
                else:
                    # Response-level error
                    error_msg = response.get("status_message", "Unknown error")
                    st.error(f"API response error: {error_msg}")
                    failed_batches += 1
                
                # Rate limiting - be nice to the API
                if chunk_idx < len(chunks) - 1:
                    time.sleep(0.5)  # 500ms delay between requests
                    
            except Exception as e:
                st.error(f"Error processing batch {chunk_idx+1}: {str(e)}")
                failed_batches += 1
                continue
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Show final summary
        if results:
            st.success(f"✅ Successfully retrieved {total_volumes_retrieved} search volumes")
            
            # Show some sample results
            if total_volumes_retrieved > 0:
                with st.expander("Sample results (first 10)"):
                    sample_results = list(results.items())[:10]
                    for kw, vol in sample_results:
                        st.write(f"• **{kw}**: {vol:,} searches/month")
            
            if failed_batches > 0:
                st.warning(f"⚠️ {failed_batches} batch{'es' if failed_batches > 1 else ''} failed")
        else:
            st.error("❌ No search volumes retrieved. Check your keywords or API credentials.")
        
        return results
