import numpy as np
from typing import Dict, List

class SimilarityEngine:
    def __init__(self):
        pass

    def compute_related_pages(self, embeddings_map: Dict[str, np.ndarray], top_k: int = 10) -> Dict[str, List[str]]:
        urls = list(embeddings_map.keys())
        if not urls:
            return {}
        vecs = [embeddings_map[u] for u in urls]
        mat = np.vstack([v / (np.linalg.norm(v) + 1e-8) for v in vecs])
        sims = mat @ mat.T
        related = {}
        for i, u in enumerate(urls):
            sim_row = sims[i]
            idxs = np.argsort(-sim_row)
            candidates = []
            for j in idxs:
                if j == i:
                    continue
                candidates.append(urls[j])
                if len(candidates) >= top_k:
                    break
            related[u] = candidates
        return related
