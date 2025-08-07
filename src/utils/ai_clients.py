import streamlit as st
from typing import Optional, List

class AIClient:
    def __init__(self, provider: str, model: str, temperature: float = 0.4):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self._init_client()

    def _init_client(self):
        if self.provider == "OpenAI":
            try:
                # Debug: Check if secrets exist
                if "openai" not in st.secrets:
                    st.error("❌ 'openai' section not found in secrets!")
                    self.client = None
                    return
                
                # Debug: Check if api_key exists
                openai_secrets = st.secrets["openai"]
                if "api_key" not in openai_secrets:
                    st.error("❌ 'api_key' not found in openai secrets!")
                    self.client = None
                    return
                
                api_key = openai_secrets["api_key"]
                
                # Debug: Check if api_key is empty or placeholder
                if not api_key or api_key == "sk-proj-YOUR-ACTUAL-KEY-HERE":
                    st.error("❌ OpenAI API key is empty or still a placeholder!")
                    self.client = None
                    return
                
                # Debug: Show key format (first few chars only)
                st.info(f"🔑 OpenAI key starts with: {api_key[:10]}...")
                
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
                st.success("✅ OpenAI client initialized successfully!")
                
            except Exception as e:
                st.error(f"❌ Error initializing OpenAI: {str(e)}")
                self.client = None
                
        elif self.provider == "Anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])
            except Exception as e:
                st.error(f"❌ Error initializing Anthropic: {str(e)}")
                self.client = None
                
        elif self.provider == "Gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                self.client = genai
            except Exception as e:
                st.error(f"❌ Error initializing Gemini: {str(e)}")
                self.client = None
        else:
            self.client = None

    def complete(self, prompt: str):
        if self.client is None:
            return None
            
        try:
            if self.provider == "OpenAI":
                resp = self.client.chat.completions.create(
                    model=self.model or "gpt-4o-mini",
                    messages=[{"role":"system","content":"You are a helpful SEO assistant."},
                              {"role":"user","content":prompt}],
                    temperature=self.temperature,
                    max_tokens=200
                )
                return resp.choices[0].message.content
            elif self.provider == "Anthropic":
                msg = self.client.messages.create(
                    model=self.model or "claude-3-haiku-20240307",
                    max_tokens=200,
                    temperature=self.temperature,
                    messages=[{"role":"user","content": prompt}]
                )
                parts = []
                for c in msg.content:
                    if hasattr(c, "text"):
                        parts.append(c.text)
                    elif isinstance(c, dict) and c.get("type") == "text":
                        parts.append(c.get("text",""))
                return " ".join(parts).strip()
            elif self.provider == "Gemini":
                m = self.client.GenerativeModel(self.model or "gemini-1.5-flash")
                out = m.generate_content(prompt)
                return out.text
            else:
                return None
        except Exception as e:
            st.error(f"❌ Error during completion: {str(e)}")
            return None

def get_available_ai_providers(cfg) -> List[str]:
    providers = []
    if cfg.openai_present: providers.append("OpenAI")
    if cfg.anthropic_present: providers.append("Anthropic")
    if cfg.gemini_present: providers.append("Gemini")
    return providers

@st.cache_resource(show_spinner=False)
def get_ai_client_cached(provider: Optional[str], model: Optional[str], temperature: float = 0.4) -> Optional[AIClient]:
    if not provider:
        return None
    return AIClient(provider, model or "", temperature)
