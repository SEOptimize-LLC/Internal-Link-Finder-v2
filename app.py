#!/usr/bin/env python3
import streamlit as st
import pandas as pd
from src.core.data_processor import EnhancedDataProcessor
from src.core.gsc_processor import GSCDataProcessor
from src.core.dataforseo_client import DataForSEOClient
from src.core.similarity_engine import SimilarityEngine
from src.analyzers.link_analyzer import EnhancedLinkAnalyzer
from src.analyzers.performance_analyzer import PerformanceAnalyzer
from src.content_generation.content_generator import InternalLinkContentGenerator
from src.utils.export_utils import ExportManager
from src.ui.components import render_status_badge, render_info_box, render_warning_box
from src.ui.workflows import render_upload_section, render_analysis_controls
from src.utils.ai_clients import get_available_ai_providers, get_ai_client_cached
from config import AppConfig

st.set_page_config(
    page_title="Enhanced Internal Link Opportunity Finder",
    page_icon="🔗",
    layout="wide",
)

def init_session():
    ss = st.session_state
    ss.setdefault("links_df", None)
    ss.setdefault("embeddings_map", None)
    ss.setdefault("gsc_raw_df", None)
    ss.setdefault("gsc_metrics_df", None)
    ss.setdefault("search_volume_map", {})
    ss.setdefault("url_keywords_map", {})
    ss.setdefault("analysis_df", None)
    ss.setdefault("suggestions_df", pd.DataFrame(columns=[
        "Target URL","Destination URL","Anchor Text","Placement Hint","Content Snippet","Status","Implementation Priority"
    ]))
    ss.setdefault("related_pages_map", {})
    ss.setdefault("processed", False)
    ss.setdefault("use_gsc_api", False)
    ss.setdefault("use_dataforseo", False)
    ss.setdefault("use_ai_for_generation", True)
    ss.setdefault("use_ai_for_extraction", True)
    ss.setdefault("gsc_domain", "")
    ss.setdefault("gsc_date_range", "Last 90 days")
    ss.setdefault("ai_provider", None)
    ss.setdefault("ai_model", "")
    ss.setdefault("ai_temperature", 0.4)
    ss.setdefault("current_client", "")  # Track current client being analyzed

init_session()

cfg = AppConfig.load()

# Sidebar: Secrets status and AI selection
st.sidebar.title("⚙️ Settings")

# Multi-client support - show current client if set
if st.session_state.current_client:
    st.sidebar.success(f"📊 Analyzing: {st.session_state.current_client}")
else:
    st.sidebar.info("📁 Upload files to begin analysis")

st.sidebar.write(f"Max Concurrency: {cfg.max_concurrency}")

# Status indicators
st.sidebar.subheader("🔌 Integration Status")
render_status_badge("GSC API", "Disabled" if not cfg.gsc_service_account_present else "Ready")
render_status_badge("DataForSEO", "OK" if cfg.dataforseo_present else "Not configured")
render_status_badge("Sheets Export", "Disabled" if not cfg.sheets_present else "Ready")
render_status_badge("OpenAI", "OK" if cfg.openai_present else "Missing")
render_status_badge("Anthropic", "OK" if cfg.anthropic_present else "Not configured")
render_status_badge("Gemini", "OK" if cfg.gemini_present else "Not configured")

available_ai = get_available_ai_providers(cfg)
st.sidebar.subheader("🤖 AI Options")
st.sidebar.checkbox("Use AI for content generation", key="use_ai_for_generation", value=True)
st.sidebar.checkbox("Use AI for keyword/entities extraction", key="use_ai_for_extraction", value=True, help="Used when GSC queries are missing or for enrichment")

if available_ai:
    st.sidebar.selectbox("AI Provider", options=available_ai, key="ai_provider")
    default_models = cfg.default_models.get(st.session_state.ai_provider, [])
    st.sidebar.text_input("Model name", value=default_models[0] if default_models else "", key="ai_model", help="Override the default model name")
    st.sidebar.slider("AI Temperature", 0.0, 1.0, value=st.session_state.ai_temperature, key="ai_temperature")
else:
    st.sidebar.error("⚠️ No AI providers configured! Please add at least one API key in secrets.")
    st.session_state.ai_provider = None

# Initialize core services
data_processor = EnhancedDataProcessor()
gsc_processor = GSCDataProcessor()
similarity_engine = SimilarityEngine()
link_analyzer = EnhancedLinkAnalyzer()
perf_analyzer = PerformanceAnalyzer()
export_manager = ExportManager()

# AI client (cached)
ai_client = get_ai_client_cached(
    provider=st.session_state.ai_provider,
    model=st.session_state.ai_model,
    temperature=st.session_state.ai_temperature
) if st.session_state.ai_provider else None

link_content_generator = InternalLinkContentGenerator(ai_client=ai_client)
dataforseo_client = DataForSEOClient() if cfg.dataforseo_present else None

tabs = st.tabs(["📤 Upload & Validate", "🔍 Analyze Opportunities", "✏️ Generate Link Content", "📊 Reports & Export"])

# Tab 1: Upload & Validate
with tabs[0]:
    st.header("📤 Upload & Validate")
    
    # Client identifier (optional but helpful for tracking)
    client_name = st.text_input("Client/Website Name (optional)", 
                                placeholder="e.g., Client ABC or example.com",
                                help="Helps you track which client you're analyzing")
    if client_name:
        st.session_state.current_client = client_name
    
    render_info_box("Upload Screaming Frog Internal Links, Embeddings, and optionally a GSC CSV export.")
    files = render_upload_section()

    # GSC Options (disabled if no service account)
    if cfg.gsc_service_account_present:
        st.checkbox("Use Google Search Console API", key="use_gsc_api", value=False)
        if st.session_state.use_gsc_api:
            st.subheader("GSC API Options")
            st.session_state.gsc_domain = st.text_input(
                "GSC Property URL", 
                value=st.session_state.gsc_domain,
                placeholder="https://www.example.com/",
                help="Enter the exact property URL as it appears in GSC"
            )
            st.session_state.gsc_date_range = st.selectbox("GSC Date range", options=["Last 28 days", "Last 90 days", "Last 180 days"], index=1)
    else:
        st.info("💡 GSC API is disabled. Upload GSC data as CSV instead (export from Search Console).")
    
    st.checkbox("Use DataForSEO for monthly search volume", key="use_dataforseo", value=cfg.dataforseo_present)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Process Files", type="primary"):
            if not files.get("links") or not files.get("embeddings"):
                render_warning_box("Please upload at least Screaming Frog Internal Links and Embeddings files.")
            else:
                with st.spinner("Processing your files..."):
                    processed = data_processor.process_multiple_files(files)
                    st.session_state.links_df = processed["links_df"]
                    st.session_state.embeddings_map = processed["embeddings_map"]
                    st.session_state.gsc_raw_df = processed.get("gsc_raw_df")
                    if st.session_state.gsc_raw_df is not None:
                        st.session_state.gsc_metrics_df = gsc_processor.calculate_url_metrics(st.session_state.gsc_raw_df)
                        st.success("✅ GSC metrics computed.")
                    st.session_state.processed = True
                    st.success(f"✅ Files processed successfully for {st.session_state.current_client or 'your website'}!")
    
    with c2:
        if st.session_state.use_gsc_api and cfg.gsc_service_account_present:
            if st.button("📥 Fetch GSC via API"):
                if not st.session_state.gsc_domain:
                    render_warning_box("Please enter a GSC property URL first.")
                else:
                    with st.spinner("Fetching GSC data..."):
                        try:
                            gsc_df = gsc_processor.fetch_gsc_api(
                                domain_property=st.session_state.gsc_domain,
                                date_range=st.session_state.gsc_date_range
                            )
                            st.session_state.gsc_raw_df = gsc_df
                            st.session_state.gsc_metrics_df = gsc_processor.calculate_url_metrics(gsc_df)
                            st.success(f"✅ Fetched {len(gsc_df):,} GSC rows.")
                        except Exception as e:
                            render_warning_box(f"GSC API error: {e}")

    if st.session_state.processed or (st.session_state.gsc_raw_df is not None):
        st.subheader("📋 Preview")
        if st.session_state.links_df is not None:
            st.write("**Links sample:**", st.session_state.links_df.head(10))
        if st.session_state.gsc_raw_df is not None:
            st.write("**GSC sample:**", st.session_state.gsc_raw_df.head(10))

# Tab 2: Analyze Opportunities
with tabs[1]:
    st.header("🔍 Analyze Opportunities")
    if not (st.session_state.embeddings_map and st.session_state.links_df is not None):
        render_warning_box("Please complete Upload & Validate first.")
    else:
        params = render_analysis_controls()

        if st.button("🔗 Compute Related Pages"):
            with st.spinner("Computing related pages via embeddings..."):
                related_pages_map = similarity_engine.compute_related_pages(
                    embeddings_map=st.session_state.embeddings_map,
                    top_k=params["top_k_related"]
                )
                st.session_state.related_pages_map = related_pages_map
                st.success(f"✅ Computed related pages for {len(related_pages_map)} URLs.")

        # Prepare keywords per URL (GSC or AI)
        if st.button("🔑 Prepare Keywords per URL"):
            if st.session_state.gsc_raw_df is not None and not st.session_state.gsc_raw_df.empty:
                url_keywords_map = gsc_processor.extract_top_keywords_by_url(st.session_state.gsc_raw_df, top_n=3)
                st.success("✅ Keywords extracted from GSC data.")
            elif st.session_state.use_ai_for_extraction and ai_client is not None:
                with st.spinner("Extracting keywords with AI (scraping URLs)..."):
                    url_keywords_map = link_content_generator.ai_extract_keywords_for_urls(list(st.session_state.embeddings_map.keys()), max_urls=200)
                st.info("✅ AI-based keyword extraction completed.")
            else:
                url_keywords_map = {}
                st.info("ℹ️ No GSC queries and AI extraction disabled; skipping keyword extraction.")
            st.session_state.url_keywords_map = url_keywords_map
            st.success(f"✅ Prepared keywords for {len(url_keywords_map)} URLs.")

        # DataForSEO volumes
        if st.session_state.use_dataforseo and dataforseo_client is not None and st.session_state.url_keywords_map:
            flat_keywords = sorted({kw for kws in st.session_state.url_keywords_map.values() for kw in kws})
            if len(flat_keywords) > 0:
                if st.button(f"📊 Fetch Search Volume for {len(flat_keywords)} keywords"):
                    with st.spinner("Fetching monthly search volumes from DataForSEO..."):
                        search_volume_map = dataforseo_client.get_monthly_search_volume(flat_keywords, location="US", language="English")
                        st.session_state.search_volume_map = {k.lower(): v for k, v in search_volume_map.items()}
                        st.success(f"✅ Retrieved volumes for {len(st.session_state.search_volume_map)} keywords.")

        if st.button("🎯 Run Opportunity Analysis", type="primary"):
            if not st.session_state.related_pages_map:
                render_warning_box("Compute Related Pages first.")
            else:
                with st.spinner("Analyzing opportunities..."):
                    analysis_df = link_analyzer.analyze_with_performance_data(
                        links_df=st.session_state.links_df,
                        related_pages_map=st.session_state.related_pages_map,
                        gsc_metrics_df=st.session_state.gsc_metrics_df,
                        search_volume_map=st.session_state.search_volume_map,
                        url_keywords_map=st.session_state.url_keywords_map,
                        top_related=params["top_k_related"]
                    )
                    analysis_df = perf_analyzer.score_opportunities(analysis_df)
                    st.session_state.analysis_df = analysis_df
                    st.success(f"✅ Analysis complete with {len(analysis_df):,} target URLs.")

        if st.session_state.analysis_df is not None:
            st.dataframe(st.session_state.analysis_df.head(100), use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Export Analysis as CSV"):
                    filename = f"{st.session_state.current_client}_analysis.csv" if st.session_state.current_client else "analysis_report.csv"
                    export_manager.export_df(st.session_state.analysis_df, filename=filename)
            with c2:
                if st.button("📊 Export Analysis as XLSX"):
                    filename = f"{st.session_state.current_client}_analysis.xlsx" if st.session_state.current_client else "analysis_report.xlsx"
                    export_manager.export_excel({"Analysis": st.session_state.analysis_df}, filename=filename)

# Tab 3: Generate Internal Link Content
with tabs[2]:
    st.header("✏️ Generate Internal Link Content")
    if st.session_state.analysis_df is None or st.session_state.related_pages_map is None:
        render_warning_box("Please run the analysis first.")
    else:
        target_urls = sorted(st.session_state.related_pages_map.keys())
        target_url = st.selectbox("Select a target URL", options=target_urls)
        suggested_destinations = st.session_state.related_pages_map.get(target_url, [])[:10]
        st.write("**Suggested destination URLs** (top by semantic similarity):")
        st.write(pd.DataFrame({"Destination URL": suggested_destinations}))
        destination_url = st.selectbox("Select a destination URL", options=suggested_destinations if suggested_destinations else target_urls)

        if st.button("✨ Generate Suggestion", type="primary"):
            with st.spinner("Generating anchor and snippet..."):
                suggestion = link_content_generator.generate_link_suggestions(
                    target_url=target_url,
                    destination_url=destination_url,
                    gsc_df=st.session_state.gsc_raw_df
                )
                st.write("**Generated Suggestion:**")
                st.json(suggestion)
                row = {
                    "Target URL": target_url,
                    "Destination URL": destination_url,
                    "Anchor Text": suggestion.get("anchor_text", ""),
                    "Placement Hint": suggestion.get("placement_hint", ""),
                    "Content Snippet": suggestion.get("content_snippet", ""),
                    "Status": "Suggested",
                    "Implementation Priority": suggestion.get("priority", 0.5)
                }
                st.session_state.suggestions_df = pd.concat([st.session_state.suggestions_df, pd.DataFrame([row])], ignore_index=True)

        st.subheader("📝 Batch Suggestions")
        st.write("Suggestions generated in this session:")
        st.dataframe(st.session_state.suggestions_df.tail(50), use_container_width=True)
        c1, c2 = st.columns(2)
        with c1:
            if len(st.session_state.suggestions_df) > 0 and st.button("💾 Export Suggestions CSV"):
                filename = f"{st.session_state.current_client}_suggestions.csv" if st.session_state.current_client else "link_suggestions.csv"
                export_manager.export_df(st.session_state.suggestions_df, filename=filename)
        with c2:
            if len(st.session_state.suggestions_df) > 0 and st.button("📊 Export Suggestions XLSX"):
                filename = f"{st.session_state.current_client}_suggestions.xlsx" if st.session_state.current_client else "link_suggestions.xlsx"
                export_manager.export_excel({"Suggestions": st.session_state.suggestions_df}, filename=filename)

# Tab 4: Reports & Export
with tabs[3]:
    st.header("📊 Reports & Export")
    
    if st.session_state.current_client:
        st.info(f"📁 Exporting data for: **{st.session_state.current_client}**")
    
    if st.session_state.analysis_df is not None:
        st.subheader("📈 Analysis Report")
        st.dataframe(st.session_state.analysis_df.head(100), use_container_width=True)
    if len(st.session_state.suggestions_df) > 0:
        st.subheader("🔗 Link Suggestions")
        st.dataframe(st.session_state.suggestions_df.tail(100), use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.session_state.analysis_df is not None and st.button("💾 Download All (CSV)"):
            filename = f"{st.session_state.current_client}_bundle.zip" if st.session_state.current_client else "reports_bundle.zip"
            export_manager.export_zip_csv({
                "analysis_report.csv": st.session_state.analysis_df,
                "link_suggestions.csv": st.session_state.suggestions_df
            }, filename=filename)
    with c2:
        if st.session_state.analysis_df is not None and st.button("📊 Download All (XLSX)"):
            filename = f"{st.session_state.current_client}_reports.xlsx" if st.session_state.current_client else "reports_bundle.xlsx"
            export_manager.export_excel({
                "Analysis": st.session_state.analysis_df,
                "Suggestions": st.session_state.suggestions_df
            }, filename=filename)
    with c3:
        if cfg.sheets_present:
            st.write("☁️ **Google Sheets Export**")
            sheet_title = st.text_input("Spreadsheet Title", 
                                       value=f"{st.session_state.current_client} Link Analysis" if st.session_state.current_client else "Internal Link Reports")
            create_new = st.checkbox("Create new spreadsheet", value=True)
            if st.button("📤 Export to Google Sheets"):
                try:
                    sheets = {}
                    if st.session_state.analysis_df is not None:
                        sheets["Analysis"] = st.session_state.analysis_df
                    if len(st.session_state.suggestions_df) > 0:
                        sheets["Suggestions"] = st.session_state.suggestions_df
                    url = export_manager.export_to_google_sheets(sheets, sheet_title, create_new=create_new)
                    st.success(f"✅ Exported to Google Sheets: {url}")
                except Exception as e:
                    render_warning_box(f"Sheets export failed: {e}")
        else:
            st.info("💡 Google Sheets export is disabled (no service account configured).")

st.caption("🔗 Enhanced Internal Link Opportunity Finder — Multi-Client SEO Tool")
