import pandas as pd
from src.core.gsc_processor import GSCDataProcessor

def test_gsc_agg():
    data = [
        {"page": "https://site.com/a", "query": "x", "clicks": 5, "impressions": 100},
        {"page": "https://site.com/a", "query": "y", "clicks": 3, "impressions": 50},
        {"page": "https://site.com/b", "query": "x", "clicks": 0, "impressions": 10},
    ]
    df = pd.DataFrame(data)
    p = GSCDataProcessor()
    agg = p.calculate_url_metrics(df)
    a_row = agg[agg["page"]=="https://site.com/a"].iloc[0]
    assert a_row["url_queries_count"] == 2
    assert a_row["url_clicks"] == 8
    assert a_row["url_impressions"] == 150
