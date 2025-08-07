import streamlit as st
from typing import Optional, List
import os
import sys

class AIClient:
    def __init__(self, provider: str, model: str, temperature: float = 0.4):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self._init_client()

    def _init_client(self):
        if self.provider == "OpenAI":
            try:
                # More aggressive proxy bypass for Streamlit Cloud
                import httpx
                
                # Monkey patch httpx.Client to ignore proxies
                original_client_init = httpx.Client.__init__
                
                def patched_init(self, **kwargs):
                    # Remove proxy-related arguments
                    kwargs.pop('proxies', None)
                    kwargs.pop('proxy', None)
                    kwargs.pop('trust_env', None)
                    original_client_init(self, **kwargs)
                
                httpx.Client.__init__ = patched_init
                
                # Now import and initialize OpenAI
                from openai import OpenAI
                api_key = st.secrets["openai"]["api_key"]
                
                # Create client with explicit configuration
                self.client = OpenAI(
                    api_key=api_key,
                    http_client=httpx.Client(
                        follow_redirects=True,
                        timeout=60.0
                    )
                )
                
                # Restore original httpx.Client.__init__
                httpx.Client.__init__ = original_client_init
                
            except Exception as e:
                st.error(f"Error initializing OpenAI: {str(e)}")
                self.client = None
                
        elif self.provider == "Anthropic":
            try:
                import anthropic
                api_key = st.secrets["anthropic"]["api_key"]
                
                # Similar fix for Anthropic if needed
                import httpx
                original_client_init = httpx.Client.__init__
                
                def patched_init(self, **kwargs):
                    kwargs.pop('proxies', None)
                    kwargs.pop('proxy', None)
                    kwargs.pop('trust_env', None)
                    original_client_init(self, **kwargs)
                
                httpx.Client.__init__ = patched_init
                self.client = anthropic.Anthropic(api_key=api_key)
                httpx.Client.__init__ = original_client_init
                
            except Exception as e:
                st.error(f"Error initializing Anthropic: {str(e)}")
                self.client = None
                
        elif self.provider == "Gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                self.client = genai
            except Exception as e:
                st.error(f"Error initializing Gemini: {str(e)}")
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
            st.error(f"Error during completion: {str(e)}")
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
