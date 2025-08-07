import re
from typing import List, Tuple

STOPWORDS = set("""
a an the and or but if then else when while for to of in on at by with from as is are was were be been being this that those these it its their your our we you i me my mine ours yours his her hers him them they he she what which who whom whose how why where
""".split())

class PhraseMatcher:
    def score_candidate(self, phrase: str, dest_keywords: List[str], existing_anchors: List[str]) -> float:
        p = phrase.strip()
        words = [w for w in re.sub(r'[^A-Za-z0-9\s\-]', '', p).lower().split() if w]
        if len(words) == 0:
            return 0.0
        score = 0.0
        if 2 <= len(words) <= 6:
            score += 1.0
        overlap = len(set(words) & set(dest_keywords[:20]))
        score += 0.2 * overlap
        if p.lower() in [a.lower() for a in existing_anchors]:
            score -= 0.8
        if words[0] in STOPWORDS:
            score -= 0.2
        return score

    def find_best_anchor(self, candidate_phrases: List[str], dest_keywords: List[str], existing_anchors: List[str]) -> Tuple[str, float]:
        cleaned = []
        for p in candidate_phrases:
            t = re.sub(r'\s+', ' ', p).strip()
            if len(t) > 2:
                cleaned.append(t)
        if not cleaned:
            return "learn more", 0.0
        scored = [(c, self.score_candidate(c, dest_keywords, existing_anchors)) for c in cleaned]
        scored.sort(key=lambda x: x[1], reverse=True)
        best, s = scored[0]
        return best, s
