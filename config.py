import streamlit as st
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class AppConfig:
    domain: str = ""
    max_concurrency: int = 3
    gsc_service_account_present: bool = False
    dataforseo_present: bool = False
    sheets_present: bool = False
    openai_present: bool = False
    anthropic_present: bool = False
    gemini_present: bool = False
    default_models: Dict[str, List[str]] = field(default_factory=dict)

    @staticmethod
    def load():
        cfg = AppConfig()
        cfg.domain = st.secrets.get("app", {}).get("domain", "")
        cfg.max_concurrency = int(st.secrets.get("app", {}).get("max_concurrency", 3))

        gsc = st.secrets.get("gsc", {})
        cfg.gsc_service_account_present = bool(gsc.get("type") == "service_account" and gsc.get("client_email"))

        dfs = st.secrets.get("dataforseo", {})
        cfg.dataforseo_present = bool(dfs.get("login") and dfs.get("password"))

        sheets = st.secrets.get("sheets", {})
        cfg.sheets_present = bool(sheets.get("type") == "service_account" and sheets.get("client_email"))

        openai = st.secrets.get("openai", {})
        cfg.openai_present = bool(openai.get("api_key"))

        anthropic = st.secrets.get("anthropic", {})
        cfg.anthropic_present = bool(anthropic.get("api_key"))

        gemini = st.secrets.get("gemini", {})
        cfg.gemini_present = bool(gemini.get("api_key"))

        cfg.default_models = {
            "OpenAI": st.secrets.get("openai", {}).get("default_models", ["gpt-4o-mini"]),
            "Anthropic": st.secrets.get("anthropic", {}).get("default_models", ["claude-3-haiku-20240307"]),
            "Gemini": st.secrets.get("gemini", {}).get("default_models", ["gemini-1.5-flash"])
        }
        return cfg
