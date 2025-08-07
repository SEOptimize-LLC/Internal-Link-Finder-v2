import streamlit as st
from typing import Optional, List
import requests
import json

class AIClient:
    def __init__(self, provider: str, model: str, temperature: float = 0.4):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.api_key = None
        self.client = None
        self._init_client()

    def _init_client(self):
        # NEVER import OpenAI or Anthropic SDKs - only use requests
        if self.provider == "OpenAI":
            self.api_key = st.secrets.get("openai", {}).get("api_key")
            if not self.api_key:
                st.error("OpenAI API key not found in secrets")
            self.client = None  # We don't use a client for OpenAI
                
        elif self.provider == "Anthropic":
            self.api_key = st.secrets.get("anthropic", {}).get("api_key")
            self.client = None  # We don't use a client for Anthropic
                
        elif self.provider == "Gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                self.client = genai
                self.api_key = st.secrets["gemini"]["api_key"]
            except Exception as e:
                st.error(f"Error initializing Gemini: {str(e)}")
                self.client = None

    def complete(self, prompt: str):
        if self.provider == "OpenAI":
            return self._openai_complete_requests(prompt)
        elif self.provider == "Anthropic":
            return self._anthropic_complete_requests(prompt)
        elif self.provider == "Gemini" and self.client:
            try:
                m = self.client.GenerativeModel(self.model or "gemini-1.5-flash")
                out = m.generate_content(prompt)
                return out.text
            except Exception as e:
                return None
        else:
            return None

    def _openai_complete_requests(self, prompt: str):
        """Direct HTTP request to OpenAI API"""
        if not self.api_key:
            return None
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a helpful SEO assistant."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": 200
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return None
                
        except Exception as e:
            return None

    def _anthropic_complete_requests(self, prompt: str):
        """Direct HTTP request to Anthropic API"""
        if not self.api_key:
            return None
            
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model or "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": self.temperature
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", "")
                return ""
            else:
                return None
                
        except Exception as e:
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
