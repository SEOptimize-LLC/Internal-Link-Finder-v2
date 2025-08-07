import pandas as pd
from typing import Dict, List

class GSCDataProcessor:
    """Processes Google Search Console data from CSV exports only"""
    
    def __init__(self):
        pass
    
    def calculate_url_metrics(self, gsc_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate aggregated metrics per URL from GSC data
        
        Args:
            gsc_data: DataFrame with GSC export data
            
        Returns:
            DataFrame with aggregated metrics per URL
        """
        if gsc_data is None or gsc_data.empty:
            return pd.DataFrame(columns=["page", "url_queries_count", "url_clicks", "url_impressions"])
        
        # Aggregate metrics by page
        agg = gsc_data.groupby("page", as_index=False).agg(
            url_queries_count=("query", "nunique"),
            url_clicks=("clicks", "sum"),
            url_impressions=("impressions", "sum")
        )
        
        return agg
    
    def extract_top_keywords_by_url(self, gsc_data: pd.DataFrame, top_n: int = 3) -> Dict[str, List[str]]:
        """
        Extract top performing keywords for each URL
        
        Args:
            gsc_data: DataFrame with GSC export data
            top_n: Number of top keywords to extract per URL
            
        Returns:
            Dictionary mapping URLs to their top keywords
        """
        if gsc_data is None or gsc_data.empty:
            return {}
        
        gsc_data = gsc_data.copy()
        
        # Rank queries by clicks for each page
        gsc_data["rank"] = gsc_data.groupby("page")["clicks"].rank("dense", ascending=False)
        top_clicks = gsc_data[gsc_data["rank"] <= top_n]
        
        # If no clicks, rank by impressions
        if top_clicks.empty:
            gsc_data["rank"] = gsc_data.groupby("page")["impressions"].rank("dense", ascending=False)
            top_clicks = gsc_data[gsc_data["rank"] <= top_n]
        
        # Build output dictionary
        out: Dict[str, List[str]] = {}
        for page, sub in top_clicks.groupby("page"):
            queries = [q for q in sub["query"].dropna().astype(str).tolist() if q]
            if queries:
                out[page] = queries
        
        return out
