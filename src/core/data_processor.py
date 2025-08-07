import pandas as pd
import numpy as np
import json
import ast
from typing import Dict, Any
from src.utils.csv_handler import safe_read_csv

class EnhancedDataProcessor:
    def __init__(self):
        pass

    def process_multiple_files(self, files_dict: Dict[str, Any]):
        links_file = files_dict.get("links")
        embeddings_file = files_dict.get("embeddings")
        gsc_file = files_dict.get("gsc")

        links_df = safe_read_csv(links_file)
        links_df = self._normalize_links_df(links_df)

        embeddings_df = safe_read_csv(embeddings_file)
        embeddings_map = self._parse_embeddings(embeddings_df)

        gsc_df = None
        if gsc_file is not None:
            gsc_df = safe_read_csv(gsc_file)
            gsc_df = self._normalize_gsc_df(gsc_df)

        return {
            "links_df": links_df,
            "embeddings_map": embeddings_map,
            "gsc_raw_df": gsc_df
        }

    def _normalize_links_df(self, df: pd.DataFrame) -> pd.DataFrame:
        source_col = next((c for c in df.columns if c.lower().strip() in ("source","from","origin")), None)
        dest_col = next((c for c in df.columns if c.lower().strip() in ("destination","to","target","link")), None)
        anchor_col = next((c for c in df.columns if c.lower().strip() in ("anchor","anchor text","anchor_text")), None)
        if not source_col or not dest_col:
            raise ValueError("Screaming Frog links CSV must contain Source and Destination columns.")
        out = pd.DataFrame({
            "Source": df[source_col].astype(str).str.strip(),
            "Destination": df[dest_col].astype(str).str.strip(),
        })
        out["Anchor"] = df[anchor_col].astype(str).str.strip() if anchor_col else ""
        out = out.dropna(subset=["Source","Destination"])
        return out

    def _parse_embeddings(self, df: pd.DataFrame):
        # Find URL column - look for variations
        url_col = None
        for c in df.columns:
            c_lower = c.lower()
            if any(term in c_lower for term in ["url", "page", "address"]):
                url_col = c
                break
        
        if url_col is None:
            raise ValueError("Embeddings CSV must include a URL/Address column.")
        
        vecs = {}
        
        # Find embedding column - look for more variations
        emb_col = None
        for c in df.columns:
            c_lower = c.lower()
            # Check for various embedding column names
            if any(term in c_lower for term in ["embedding", "vector", "extract embedding", "page content"]):
                emb_col = c
                break
        
        if emb_col:
            # Parse embeddings from the found column
            for _, row in df.iterrows():
                url = str(row[url_col]).strip()
                raw = row[emb_col]
                if pd.isna(raw):
                    continue
                try:
                    # Try to parse as JSON first
                    if isinstance(raw, str):
                        # Remove any potential formatting
                        raw = raw.strip()
                        if raw.startswith('[') and raw.endswith(']'):
                            v = json.loads(raw)
                        else:
                            # Try to evaluate as Python literal
                            v = ast.literal_eval(raw)
                    else:
                        v = raw
                    
                    # Convert to numpy array
                    vecs[url] = np.array(v, dtype="float32")
                except Exception as e:
                    # Skip rows that can't be parsed
                    continue
            
            if vecs:
                return vecs
        
        # Check for multiple embedding columns (emb_0, emb_1, etc.)
        emb_cols = [c for c in df.columns if str(c).lower().startswith("emb_")]
        if len(emb_cols) > 0:
            emb_cols_sorted = sorted(emb_cols, key=lambda x: int(str(x).split("_")[1]) if "_" in str(x) and str(x).split("_")[1].isdigit() else 0)
            for _, row in df.iterrows():
                url = str(row[url_col]).strip()
                v = row[emb_cols_sorted].astype(float).to_numpy(dtype="float32")
                vecs[url] = v
            return vecs
        
        # If we still haven't found embeddings, provide more helpful error
        raise ValueError(f"Could not find embeddings in CSV. Found columns: {', '.join(df.columns[:10])}... Please ensure your embeddings are in a column containing 'embedding' or 'vector' in the name.")

    def _normalize_gsc_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize GSC data with flexible column name matching"""
        if df is None or df.empty:
            return df
        
        # Create a mapping for standard column names
        rename_map = {}
        
        # Find page/URL column (most important)
        page_col = None
        for c in df.columns:
            c_lower = c.lower().strip()
            # Check for various page/URL column names
            if any(term in c_lower for term in ["page", "url", "address", "landing"]):
                page_col = c
                rename_map[c] = "page"
                break
        
        # If no page column found, raise error with helpful message
        if page_col is None:
            available_cols = ', '.join(df.columns[:10])
            raise ValueError(f"GSC data must have a page/URL column. Found columns: {available_cols}...")
        
        # Find query column
        for c in df.columns:
            c_lower = c.lower().strip()
            if c_lower in ("query", "queries", "keyword", "keywords", "search term", "search query"):
                rename_map[c] = "query"
                break
        
        # Find clicks column
        for c in df.columns:
            c_lower = c.lower().strip()
            if "click" in c_lower:
                rename_map[c] = "clicks"
                break
        
        # Find impressions column
        for c in df.columns:
            c_lower = c.lower().strip()
            if "impression" in c_lower:
                rename_map[c] = "impressions"
                break
        
        # Find CTR column
        for c in df.columns:
            c_lower = c.lower().strip()
            if "ctr" in c_lower or "click through" in c_lower or "clickthrough" in c_lower:
                rename_map[c] = "ctr"
                break
        
        # Find position column
        for c in df.columns:
            c_lower = c.lower().strip()
            if "position" in c_lower or "ranking" in c_lower or "rank" in c_lower:
                rename_map[c] = "position"
                break
        
        # Find date column (if exists)
        for c in df.columns:
            c_lower = c.lower().strip()
            if "date" in c_lower:
                rename_map[c] = "date"
                break
        
        # Apply the rename mapping
        df = df.rename(columns=rename_map)
        
        # Convert data types for known columns
        if "clicks" in df.columns: 
            df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce").fillna(0).astype(int)
        if "impressions" in df.columns: 
            df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce").fillna(0).astype(int)
        if "ctr" in df.columns: 
            # Handle percentage formats (e.g., "5.2%" -> 0.052)
            if df["ctr"].dtype == 'object':
                df["ctr"] = df["ctr"].astype(str).str.rstrip('%').astype('float') / 100.0
            else:
                df["ctr"] = pd.to_numeric(df["ctr"], errors="coerce").fillna(0.0)
        if "position" in df.columns: 
            df["position"] = pd.to_numeric(df["position"], errors="coerce").fillna(0.0)
        if "page" in df.columns: 
            df["page"] = df["page"].astype(str).str.strip()
        if "query" in df.columns: 
            df["query"] = df["query"].astype(str).str.strip()
        
        return df
