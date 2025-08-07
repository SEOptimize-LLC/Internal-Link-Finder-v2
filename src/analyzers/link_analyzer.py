import pandas as pd
from typing import Dict, List

class EnhancedLinkAnalyzer:
    def __init__(self):
        pass

    def analyze_with_performance_data(self,
                                      links_df: pd.DataFrame,
                                      related_pages_map: Dict[str, List[str]],
                                      gsc_metrics_df: pd.DataFrame,
                                      search_volume_map: Dict[str, int],
                                      url_keywords_map: Dict[str, List[str]],
                                      top_related: int = 10) -> pd.DataFrame:
        metrics = {}
        if gsc_metrics_df is not None and not gsc_metrics_df.empty:
            for _, r in gsc_metrics_df.iterrows():
                metrics[str(r["page"]).strip()] = {
                    "queries": int(r.get("url_queries_count", 0)),
                    "clicks": int(r.get("url_clicks", 0)),
                    "impressions": int(r.get("url_impressions", 0)),
                }
        else:
            metrics = {u: {"queries": 0, "clicks": 0, "impressions": 0} for u in related_pages_map.keys()}

        rows = []
        for target_url, related_urls in related_pages_map.items():
            m = metrics.get(target_url, {"queries": 0, "clicks": 0, "impressions": 0})

            msv = 0
            kws = url_keywords_map.get(target_url, []) if url_keywords_map else []
            vols = [search_volume_map.get(kw.lower(), search_volume_map.get(kw, 0)) for kw in kws]
            if vols:
                msv = max(vols) if len(vols) > 0 else 0

            base = {
                "Target URL": target_url,
                "# of Queries": m["queries"],
                "Clicks": m["clicks"],
                "Impressions": m["impressions"],
                "Monthly Search Volume": msv,
            }

            for i in range(top_related):
                col_u = f"Related URL {i+1}"
                col_s = f"URL {i+1} Status"
                val_u = related_urls[i] if i < len(related_urls) else ""
                status = self._link_status(links_df, source=target_url, destination=val_u)
                base[col_u] = val_u
                base[col_s] = status
            rows.append(base)

        df = pd.DataFrame(rows)
        return df

    def _link_status(self, links_df: pd.DataFrame, source: str, destination: str) -> str:
        if not source or not destination:
            return ""
        sub = links_df[(links_df["Source"] == source) & (links_df["Destination"] == destination)]
        if len(sub) > 0:
            return "Exists"
        return "Missing"
