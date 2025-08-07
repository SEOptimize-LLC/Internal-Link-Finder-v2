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
        url_col = next((c for c in df.columns if c.lower() in ("url","page","address")), None)
        if url_col is None:
            raise ValueError("Embeddings CSV must include a URL column.")
        vecs = {}
        emb_col = next((c for c in df.columns if c.lower() in ("embedding","vector")), None)
        if emb_col:
            for _, row in df.iterrows():
                url = str(row[url_col]).strip()
                raw = row[emb_col]
                if pd.isna(raw):
                    continue
                try:
                    if isinstance(raw, str):
                        v = json.loads(raw)
                    else:
                        v = raw
                except Exception:
                    try:
                        v = ast.literal_eval(str(raw))
                    except Exception:
                        continue
                try:
                    vecs[url] = np.array(v, dtype="float32")
                except Exception:
                    continue
            return vecs
        emb_cols = [c for c in df.columns if str(c).lower().startswith("emb_")]
        if len(emb_cols) > 0:
            emb_cols_sorted = sorted(emb_cols, key=lambda x: int(str(x).split("_")[1]) if "_" in str(x) and str(x).split("_")[1].isdigit() else 0)
            for _, row in df.iterrows():
                url = str(row[url_col]).strip()
                v = row[emb_cols_sorted].astype(float).to_numpy(dtype="float32")
                vecs[url] = v
            return vecs
        raise ValueError("Embeddings CSV must have an 'embedding' column or multiple 'emb_#' columns.")

    def _normalize_gsc_df(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {}
        for c in df.columns:
            lc = c.lower().strip()
            if lc in ("date","page","query","clicks","impressions","ctr","position"):
                rename_map[c] = lc
        df = df.rename(columns=rename_map)
        if "clicks" in df.columns: df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce").fillna(0).astype(int)
        if "impressions" in df.columns: df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce").fillna(0).astype(int)
        if "ctr" in df.columns: df["ctr"] = pd.to_numeric(df["ctr"], errors="coerce").fillna(0.0)
        if "position" in df.columns: df["position"] = pd.to_numeric(df["position"], errors="coerce").fillna(0.0)
        if "page" in df.columns: df["page"] = df["page"].astype(str).str.strip()
        if "query" in df.columns: df["query"] = df["query"].astype(str).str.strip()
        return df
