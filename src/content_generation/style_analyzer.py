import re
import statistics

class StyleAnalyzer:
    def analyze(self, text: str):
        if not text:
            return {"avg_sentence_len": 18, "tone": "neutral", "variant": "American"}
        sents = re.split(r'[.!?]\s+', text)
        lens = [len(s.split()) for s in sents if s.strip()]
        avg = statistics.mean(lens) if lens else 18
        tone = "informative" if avg >= 16 else "conversational"
        return {"avg_sentence_len": int(avg), "tone": tone, "variant": "American"}
