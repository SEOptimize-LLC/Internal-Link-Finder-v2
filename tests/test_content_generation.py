from src.content_generation.content_generator import InternalLinkContentGenerator

def test_generate_suggestion_basic():
    gen = InternalLinkContentGenerator()
    s = gen.generate_link_suggestions("https://example.com/path/topic", "https://example.com/dest")
    assert "anchor_text" in s and s["anchor_text"]
    assert "content_snippet" in s
