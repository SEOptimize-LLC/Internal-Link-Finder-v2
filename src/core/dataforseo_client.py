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
    
    # DataForSEO limits (based on actual API behavior)
    MAX_KEYWORD_LENGTH = 80  # Maximum characters
    MAX_KEYWORD_WORDS = 10   # Maximum number of words (based on error messages)
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

    def _clean_and_validate_keyword(self, keyword: str) -> tuple[str, str]:
        """
        Clean and validate keyword according to DataForSEO requirements.
        Returns: (cleaned_keyword, skip_reason) - skip_reason is empty string if valid
        """
        # Remove quotes and special characters
        keyword = keyword.replace('"', '').replace("'", '').replace('"', '').replace('"', '')
        keyword = keyword.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        # Remove problematic punctuation but keep spaces and hyphens
        keyword = re.sub(r'[^\w\s\-]', ' ', keyword)
        
        # Clean up multiple spaces
        keyword = ' '.join(keyword.split())
        keyword = keyword.strip()
        
        # Check character length
        if len(keyword) < self.MIN_KEYWORD_LENGTH:
            return "", "Too short"
        
        if len(keyword) > self.MAX_KEYWORD_LENGTH:
            # Try to truncate at word boundary
            words = keyword.split()
            truncated = ""
            for word in words:
                if len(truncated + " " + word) <= self.MAX_KEYWORD_LENGTH:
                    truncated = (truncated + " " + word).strip()
                else:
                    break
            keyword = truncated
            if len(keyword) < self.MIN_KEYWORD_LENGTH:
                return "", f"Too long ({len(keyword)} chars after truncation)"
        
        # Check word count
        word_count = len(keyword.split())
        if word_count > self.MAX_KEYWORD_WORDS:
            # Keep only first N words
            words = keyword.split()[:self.MAX_KEYWORD_WORDS]
            keyword = ' '.join(words)
            # Note: we truncated but still return as valid
        
        # Final validation
        word_count = len(keyword.split())
        if word_count > self.MAX_KEYWORD_WORDS:
            return "", f"Too many words ({word_count} words)"
        
        if len(keyword) < self.MIN_KEYWORD_LENGTH:
            return "", "Too short after cleaning"
        
        if len(keyword) > self.MAX_KEYWORD_LENGTH:
            return "", f"Too long ({len(keyword)} chars)"
        
        return keyword, ""

    def get_monthly_search_volume(self, keywords: List[str], location: str = "US", language: str = "English") -> Dict[str, int]:
        """
        Get monthly search volumes for keywords using DataForSEO clickstream endpoint.
        """
        if not keywords:
            return {}
        
        # Process and validate keywords
        valid_keywords = []
        skipped_keywords = []
        original_to_cleaned = {}
        
        for original_kw in keywords:
            cleaned_kw, skip_reason = self._clean_and_validate_keyword(original_kw)
            
            if cleaned_kw and not skip_reason:
                valid_keywords.append(cleaned_kw)
                original_to_cleaned[original_kw.lower()] = cleaned_kw.lower()
            else:
                skipped_keywords.append((original_kw, skip_reason))
        
        # Remove duplicates
        seen = set()
        unique_keywords = []
        for kw in valid_keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)
        
        # Report statistics
        st.write("### Keyword Processing Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Original Keywords", len(keywords))
        with col2:
            st.metric("Valid Keywords", len(unique_keywords))
        with col3:
            st.metric("Skipped Keywords", len(skipped_keywords))
        
        if skipped_keywords:
            with st.expander(f"⚠️ Skipped {len(skipped_keywords)} keywords (too long/many words)"):
                # Group by skip reason
                reasons = {}
                for kw, reason in skipped_keywords:
                    if reason not in reasons:
                        reasons[reason] = []
                    reasons[reason].append(kw)
                
                for reason, kws in reasons.items():
                    st.write(f"**{reason}** ({len(kws)} keywords):")
                    for kw in kws[:5]:  # Show first 5 of each type
                        display_kw = kw[:60] + "..." if len(kw) > 60 else kw
                        word_count = len(kw.split())
                        st.write(f"  • {display_kw} ({word_count} words, {len(kw)} chars)")
                    if len(kws) > 5:
                        st.write(f"  ... and {len(kws) - 5} more")
        
        if not unique_keywords:
            st.error("❌ No valid keywords after filtering. All keywords exceeded word/character limits.")
            st.info("💡 Try using shorter, more focused keywords (max 10 words, 80 characters)")
            return {}
        
        # Show what we're sending
        with st.expander("📤 Keywords being sent to API"):
            sample_size = min(20, len(unique_keywords))
            st.write(f"Showing first {sample_size} of {len(unique_keywords)} keywords:")
            for kw in unique_keywords[:sample_size]:
                word_count = len(kw.split())
                st.write(f"• {kw} ({word_count} words)")
        
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
                
                # Final safety check - ensure no keyword exceeds limits
                safe_chunk = []
                for kw in chunk:
                    word_count = len(kw.split())
                    if word_count <= self.MAX_KEYWORD_WORDS and len(kw) <= self.MAX_KEYWORD_LENGTH:
                        safe_chunk.append(kw)
                    else:
                        st.warning(f"Skipping keyword in batch: '{kw[:50]}...' ({word_count} words)")
                
                if not safe_chunk:
                    st.warning(f"Batch {chunk_idx + 1}: All keywords invalid after final check")
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
                                        # Store result
                                        kw_lower = kw.lower()
                                        results[kw_lower] = vol
                                        successful_keywords += 1
                                        
                                        # Map back to original
                                        for orig, cleaned in original_to_cleaned.items():
                                            if cleaned == kw_lower:
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
                failed_batches.append(f"Batch {chunk_idx + 1}: {str(e)[:100]}")
                continue
        
        # Clear progress
        progress_bar.empty()
        status_text.empty()
        
        # Final report
        if successful_keywords > 0:
            st.success(f"✅ Retrieved search volumes for {successful_keywords} keywords")
            
            # Show sample results
            with st.expander("📊 Sample search volume results"):
                sample = list(results.items())[:20]
                if sample:
                    for kw, vol in sample:
                        st.write(f"• **{kw}**: {vol:,} searches/month")
        
        if failed_batches:
            with st.expander(f"❌ Failed batches ({len(failed_batches)})"):
                for error in failed_batches:
                    st.write(f"• {error}")
        
        if not results:
            st.error("❌ No search volumes retrieved.")
            st.info("💡 Try using keywords with max 10 words and 80 characters")
        
        return results
