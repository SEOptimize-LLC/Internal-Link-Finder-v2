import pandas as pd
import numpy as np

class PerformanceAnalyzer:
    def __init__(self):
        pass

    def score_opportunities(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        x = df.copy()
        imp = x["Impressions"].astype(float).fillna(0)
        clk = x["Clicks"].astype(float).fillna(0)
        ctr = (clk / imp.replace(0, np.nan)).fillna(0.0)
        opp = (imp - clk).clip(lower=0)

        def norm(s):
            m = s.max()
            return (s / m) if m > 0 else s
        x["OppScore"] = 0.6 * norm(opp) + 0.4 * (1 - norm(ctr))
        x["Implementation Priority"] = pd.cut(x["OppScore"], bins=[-0.01,0.33,0.66,1.0], labels=["Low","Medium","High"])
        return x
