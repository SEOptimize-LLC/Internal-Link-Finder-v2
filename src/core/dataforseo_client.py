import base64
import json
import time
from typing import List, Dict
import requests
import streamlit as st
import re

class DataForSEOClient:
    # Using the clickstream endpoint
    BASE_URL = "https://api.dataforseo.com/v3/keywords_data/clickstream_data/dataforseo_search_volume/live"
    
    # Conservative limits based on actual API behavior
    MAX_KEYWORD_LENGTH = 80  # Being conservative - API seems to reject longer ones
    MAX_KEYWORDS_PER_REQUEST = 1000  
    MIN_KEYWORD_LENGTH = 1  

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
                error_text = e.response.text[:500]
                st.error(f"Response: {error_text}")
            raise

    def _clean_and_truncate_keyword(self, keyword: str) -> str:
        """Aggressively clean and truncate keywords to meet API requirements"""
        # Remove any quotes (single or double)
        keyword = keyword.replace('"', '').replace("'", '').replace('"', '').replace('"', '')
        
        # Remove other problematic characters
        keyword = keyword.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        # Replace multiple spaces with single space
        keyword = re.sub(r'\s+', ' ', keyword)
        
        # Remove special characters that might cause issues (keep only alphanumeric, spaces, and basic punctuation)
        # Keep: letters, numbers, spaces, hyphens, and basic punctuation
        keyword = re.sub(r'[^a-zA-Z0-9\s\-\.\,]', ' ', keyword)
        
        # Clean up any resulting multiple spaces
        keyword = ' '.join(keyword.split())
        
        # Trim to max length
        if len(keyword) > self.MAX_KEYWORD_LENGTH:
            # Cut at word boundary to keep it readable
            keyword = keyword[:self.MAX_KEYWORD_LENGTH]
            # Try to cut at last space to avoid partial words
            last_space = keyword.rfind(' ')
            if last_space > 50:  # Only cut at space if we're keeping at least 50 chars
                keyword = keyword[:last_space]
        
        return keyword.strip()

    def get_monthly_search_volume(self, keywords: List[str], location: str = "US", language: str = "English") -> Dict[str, int]:
        """
        Get monthly search volumes for keywords using DataForSEO clickstream endpoint.
        """
        if not keywords:
            return {}
        
        # Clean and validate keywords
        valid_keywords = []
        skipped_keywords = []
        original_to_cleaned = {}  # Map original to cleaned for result mapping
        
        for original_kw in keywords:
            # Store original (lowercased) for mapping
            original_lower = original_kw.lower()
            
            # Clean the keyword
            cleaned_kw = self._clean_and_truncate_keyword(original_kw)
            
            # Validate
            if self.MIN_KEYWORD_LENGTH <= len(cleaned_kw) <= self.MAX_KEYWORD_LENGTH:
                valid_keywords.append(cleaned_kw)
                original_to_cleaned[original_lower] = cleaned_kw.lower()
            else:
                reason = f"Too {'short' if len(cleaned_kw) < self.MIN_KEYWORD_LENGTH else 'long'} ({len(cleaned_kw)} chars)"
                skipped_keywords.append((original_kw, reason))
        
        # Remove duplicates
        seen = set()
        unique_keywords = []
        for kw in valid_keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)
        
        # Report what we're doing
        if skipped_keywords:
            st.warning(f"⚠️ Skipped {len(skipped_keywords)} keywords (too long/short or invalid)")
            with st.expander(f"Skipped keywords"):
                for kw, reason in skipped_keywords[:20]:
                    if len(kw) > 80:
                        display_kw = kw[:77] + "..."
                    else:
                        display_kw = kw
                    st.write(f"• {display_kw} - {reason}")
                if len(skipped_keywords) > 20:
                    st.write(f"... and {len(skipped_keywords) - 20} more")
        
        if not unique_keywords:
            st.error("No valid keywords after cleaning. All keywords were too long or invalid.")
            return {}
        
        st.info(f"📊 Sending {len(unique_keywords)} keywords to DataForSEO (from {len(keywords)} original)")
        
        results: Dict[str, int] = {}
        
        # Location mapping
        location_name_map = {
            "US": "United States",
            "USA": "United States", 
            "UK": "United Kingdom",
            "GB": "United Kingdom",
            "CA": "Canada",
            "AU": "Australia"
        }
        location_name = location_name_map.get(location, location)
        
        # Process in chunks
        chunks = [unique_keywords[i:i+self.MAX_KEYWORDS_PER_REQUEST] 
                 for i in range(0, len(unique_keywords), self.MAX_KEYWORDS_PER_REQUEST)]
        
        successful_keywords = 0
        failed_batches = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for chunk_idx, chunk in enumerate(chunks):
            try:
                # Update progress
                progress = (chunk_idx + 1) / len(chunks)
                progress_bar.progress(progress)
                status_text.text(f"Processing batch {chunk_idx + 1} of {len(chunks)} ({len(chunk)} keywords)...")
                
                # Double-check chunk keywords aren't too long (safety check)
                safe_chunk = [kw for kw in chunk if len(kw) <= self.MAX_KEYWORD_LENGTH]
                
                if not safe_chunk:
                    st.warning(f"Batch {chunk_idx + 1}: All keywords too long after safety check, skipping")
                    continue
                
                # Build request
                post_data = dict()
                post_data[0] = dict(
                    keywords=safe_chunk,
                    location_name=location_name,
                    language_name=language
                )
                
                # Make request
                response = self._post(post_data)
                
                # Process response
                if response.get("status_code") == 20000:
                    tasks = response.get("tasks", [])
                    for task in tasks:
                        if task.get("status_code") == 20000:
                            result_data = task.get("result", [])
                            for result in result_data:
                                items = result.get("items", [])
                                for item in items:
                                    kw = item.get("keyword", "")
                                    vol = item.get("search_volume", 0) or 0
                                    
                                    if kw:
                                        # Store with the cleaned keyword
                                        results[kw.lower()] = vol
                                        successful_keywords += 1
                                        
                                        # Also try to map back to original
                                        for orig, cleaned in original_to_cleaned.items():
                                            if cleaned == kw.lower():
                                                results[orig] = vol
                        else:
                            error_msg = task.get("status_message", "Unknown error")
                            failed_batches.append(f"Batch {chunk_idx + 1}: {error_msg}")
                else:
                    error_msg = response.get("status_message", "Unknown error")
                    failed_batches.append(f"Batch {chunk_idx + 1}: {error_msg}")
                
                # Rate limit
                if chunk_idx < len(chunks) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                failed_batches.append(f"Batch {chunk_idx + 1}: {str(e)}")
                continue
        
        # Clear progress
        progress_bar.empty()
        status_text.empty()
        
        # Report results
        if successful_keywords > 0:
            st.success(f"✅ Retrieved search volumes for {successful_keywords} keywords")
            
            # Show sample
            with st.expander("Sample results"):
                sample = list(results.items())[:10]
                for kw, vol in sample:
                    st.write(f"• **{kw}**: {vol:,} searches/month")
        
        if failed_batches:
            with st.expander(f"⚠️ {len(failed_batches)} batch errors"):
                for error in failed_batches[:5]:
                    st.write(f"• {error}")
                if len(failed_batches) > 5:
                    st.write(f"... and {len(failed_batches) - 5} more")
        
        if not results:
            st.error("❌ No search volumes retrieved. Check the error messages above.")
        
        return results
