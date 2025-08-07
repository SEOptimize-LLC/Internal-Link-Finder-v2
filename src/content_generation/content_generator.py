from typing import Dict, List
from urllib.parse import urlparse
from .scraper import EnhancedScraper
from .style_analyzer import StyleAnalyzer
from .phrase_matcher import PhraseMatcher

class QualityAssurance:
    def validate(self, anchor: str, snippet: str) -> Dict[str, str]:
        notes = []
        if len(anchor.split()) < 2:
            notes.append("Anchor too short; consider 2-5 words.")
        if len(anchor) > 60:
            notes.append("Anchor too long; keep under 60 chars.")
        if len(snippet) > 350:
            notes.append("Snippet long; keep under ~300 chars.")
        status = "OK" if not notes else "Review"
        return {"status": status, "notes": "; ".join(notes)}

class InternalLinkContentGenerator:
    def __init__(self, ai_client=None):
        self.scraper = EnhancedScraper()
        self.style_analyzer = StyleAnalyzer()
        self.phrase_matcher = PhraseMatcher()
        self.quality_assurance = QualityAssurance()
        self.ai = ai_client

    def _derive_anchor_candidates(self, target_url: str, gsc_df, dest_page_data: dict) -> List[str]:
        candidates = []
        if gsc_df is not None and not gsc_df.empty:
            sub = gsc_df[gsc_df["page"] == target_url].sort_values(["clicks","impressions"], ascending=False)
            candidates.extend(list(sub["query"].dropna().unique()[:5]))
        path = urlparse(target_url).path.strip("/")
        parts = [p.replace("-", " ").replace("_", " ") for p in path.split("/") if p]
        if parts:
            candidates.append(parts[-1])
        candidates.extend(dest_page_data.get("headings", [])[:5])
        candidates.extend(dest_page_data.get("keywords", [])[:5])
        seen = set()
        uniq = []
        for c in candidates:
            k = c.lower().strip()
            if k and k not in seen:
                uniq.append(c)
                seen.add(k)
        return uniq or ["learn more"]

    def _ai_refine_anchor(self, anchor: str, target_url: str, destination_url: str, style: dict) -> str:
        if not self.ai:
            return anchor
        prompt = f"""
You are assisting with internal linking. Propose a concise, natural anchor text (2-5 words) that points from the target page to the destination page.
Constraints:
- Avoid brand names or overly generic anchors (e.g., "click here", "learn more").
- Reflect the topic: {anchor}
- Keep <= 60 characters.
- Style: {style.get('tone','neutral')}, {style.get('variant','American')} English.
Return only the anchor text.
Target URL: {target_url}
Destination URL: {destination_url}
Initial candidate: "{anchor}"
"""
        out = self.ai.complete(prompt)
        if out:
            out = out.strip().strip('"').strip("'")
            if len(out.split()) >= 2 and len(out) <= 60:
                return out
        return anchor

    def _ai_generate_snippet(self, anchor: str, destination_url: str, style: dict) -> str:
        base = f"In our guide on {anchor}, we cover key details and practical steps. {anchor.capitalize()} can help you navigate this topic more effectively."
        if not self.ai:
            return base
        prompt = f"""
Write a single-sentence internal linking snippet (max 35 words) that naturally encourages clicking to a related internal page.
Use {style.get('tone','informative')} tone, {style.get('variant','American')} English. Avoid salesy language or over-optimization. Include the anchor phrase exactly once.
Anchor: "{anchor}"
Destination: {destination_url}
"""
        out = self.ai.complete(prompt)
        if out:
            text = out.strip().replace("\\n"," ")
            if 10 <= len(text.split()) <= 35:
                return text
        return base

    def generate_link_suggestions(self, target_url: str, destination_url: str, gsc_df=None):
        dest_data = self.scraper.fetch_page_data(destination_url)
        dest_text = dest_data.get("text","")
        style = self.style_analyzer.analyze(dest_text)
        candidates = self._derive_anchor_candidates(target_url, gsc_df, dest_data)
        existing_anchors = []
        anchor, _ = self.phrase_matcher.find_best_anchor(candidates, dest_data.get("keywords", []), existing_anchors)
        anchor = self._ai_refine_anchor(anchor, target_url, destination_url, style)
        placement = "Within the first 2-3 paragraphs, near discussion of the linked topic."
        content_snippet = self._ai_generate_snippet(anchor, destination_url, style)
        qa = self.quality_assurance.validate(anchor, content_snippet)
        priority = 0.75 if qa["status"] == "OK" else 0.5
        return {
            "anchor_text": anchor,
            "placement_hint": placement,
            "content_snippet": content_snippet,
            "style": style,
            "qa": qa,
            "priority": priority
        }

    def ai_extract_keywords_for_urls(self, urls: List[str], max_urls: int = 200) -> dict:
        out = {}
        if not self.ai:
            return out
        for i, u in enumerate(urls[:max_urls]):
            data = self.scraper.fetch_page_data(u)
            text = data.get("text","")
            if not text:
                continue
            prompt = f"""
Extract 3 to 5 short, search-relevant keywords or keyphrases from the following page content.
Return a comma-separated list only.
Content:
{text[:4000]}
"""
            res = self.ai.complete(prompt)
            if res:
                kws = [k.strip() for k in res.split(",") if k.strip()]
                out[u] = kws[:5]
        return out
