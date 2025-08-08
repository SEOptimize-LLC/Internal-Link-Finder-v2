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
    ss.setdefault("use_dataforseo", False)
    ss.setdefault("use_ai_for_generation", True)
    ss.setdefault("use_ai_for_extraction", True)
    ss.setdefault("ai_provider", None)
    ss.setdefault("ai_model", "")
    ss.setdefault("ai_temperature", 0.4)
    ss.setdefault("current_client", "")

init_session()

cfg = AppConfig.load()

# Sidebar: Settings and Status
st.sidebar.title("⚙️ Settings")

# Multi-client support
if st.session_state.current_client:
    st.sidebar.success(f"📊 Analyzing: {st.session_state.current_client}")
else:
    st.sidebar.info("📁 Upload files to begin analysis")

st.sidebar.write(f"Max Concurrency: {cfg.max_concurrency}")

# Status indicators (simplified)
st.sidebar.subheader("🔌 Integration Status")
render_status_badge("DataForSEO", "✅ Ready" if cfg.dataforseo_present else "➖ Optional")
render_status_badge("OpenAI", "✅ Ready" if cfg.openai_present else "❌ Required")
render_status_badge("Anthropic", "✅ Ready" if cfg.anthropic_present else "➖ Optional")
render_status_badge("Gemini", "✅ Ready" if cfg.gemini_present else "➖ Optional")

# AI Configuration
available_ai = get_available_ai_providers(cfg)
st.sidebar.subheader("🤖 AI Configuration")
st.sidebar.checkbox("Use AI for content generation", key="use_ai_for_generation", value=True)
st.sidebar.checkbox("Use AI for keyword extraction", key="use_ai_for_extraction", value=True, 
                   help="Extracts keywords from pages when GSC data is not available")

if available_ai:
    st.sidebar.selectbox("AI Provider", options=available_ai, key="ai_provider")
    default_models = cfg.default_models.get(st.session_state.ai_provider, [])
    st.sidebar.text_input("Model", value=default_models[0] if default_models else "", key="ai_model", 
                         help="Specify the AI model to use")
    st.sidebar.slider("Temperature", 0.0, 1.0, value=st.session_state.ai_temperature, key="ai_temperature",
                     help="Higher values = more creative, lower = more focused")
else:
    st.sidebar.error("⚠️ No AI providers configured! Add at least one API key in secrets.")
    st.session_state.ai_provider = None

# Initialize core services
data_processor = EnhancedDataProcessor()
gsc_processor = GSCDataProcessor()
similarity_engine = SimilarityEngine()
link_analyzer = EnhancedLinkAnalyzer()
perf_analyzer = PerformanceAnalyzer()
export_manager = ExportManager()

# AI client
ai_client = get_ai_client_cached(
    provider=st.session_state.ai_provider,
    model=st.session_state.ai_model,
    temperature=st.session_state.ai_temperature
) if st.session_state.ai_provider else None

link_content_generator = InternalLinkContentGenerator(ai_client=ai_client)
dataforseo_client = DataForSEOClient() if cfg.dataforseo_present else None

# Main content area with tabs
tabs = st.tabs(["📤 Upload & Process", "🔍 Analyze Links", "✏️ Generate Content", "📊 Export Results"])

# Tab 1: Upload & Process
with tabs[0]:
    st.header("📤 Upload & Process Files")
    
    # Client identifier
    col1, col2 = st.columns([2, 1])
    with col1:
        client_name = st.text_input("Client/Website Name (optional)", 
                                   value=st.session_state.current_client,
                                   placeholder="e.g., Client ABC or example.com",
                                   help="Helps track and name exports for different clients")
        if client_name:
            st.session_state.current_client = client_name
    
    with col2:
        st.checkbox("Use DataForSEO", key="use_dataforseo", 
                   value=cfg.dataforseo_present,
                   disabled=not cfg.dataforseo_present,
                   help="Fetch search volume data (requires DataForSEO account)")
    
    st.divider()
    
    # File upload section
    st.subheader("📁 Required Files")
    render_info_box("""
    **Required files from Screaming Frog:**
    1. **Internal Links CSV** - Export from Internal tab
    2. **Embeddings CSV** - Export after generating embeddings
    
    **Optional:**
    3. **GSC Data CSV** - Export from Google Search Console Performance report
    """)
    
    files = render_upload_section()
    
    # Instructions for GSC export
    with st.expander("📖 How to export GSC data"):
        st.markdown("""
        1. Go to [Google Search Console](https://search.google.com/search-console)
        2. Select your property
        3. Navigate to **Performance** → **Search results**
        4. Set your date range (recommended: Last 3 months)
        5. Enable all metrics: Clicks, Impressions, CTR, Position
        6. Click **+ New** and add dimensions: **Page** and **Query**
        7. Click **Export** (top right) → **Export CSV**
        8. Upload the CSV file here
        """)
    
    # Process button
    if st.button("🚀 Process Files", type="primary", use_container_width=True):
        if not files.get("links") or not files.get("embeddings"):
            render_warning_box("⚠️ Please upload at least Internal Links and Embeddings CSV files from Screaming Frog.")
        else:
            with st.spinner("Processing your files..."):
                try:
                    processed = data_processor.process_multiple_files(files)
                    st.session_state.links_df = processed["links_df"]
                    st.session_state.embeddings_map = processed["embeddings_map"]
                    st.session_state.gsc_raw_df = processed.get("gsc_raw_df")
                    
                    if st.session_state.gsc_raw_df is not None:
                        st.session_state.gsc_metrics_df = gsc_processor.calculate_url_metrics(st.session_state.gsc_raw_df)
                        st.success(f"✅ GSC metrics computed from {len(st.session_state.gsc_raw_df):,} rows")
                    
                    st.session_state.processed = True
                    client_msg = f" for **{st.session_state.current_client}**" if st.session_state.current_client else ""
                    st.success(f"✅ Files processed successfully{client_msg}!")
                    
                    # Show summary
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("URLs with embeddings", len(st.session_state.embeddings_map))
                    with col2:
                        st.metric("Internal links found", len(st.session_state.links_df) if st.session_state.links_df is not None else 0)
                    with col3:
                        st.metric("GSC queries", len(st.session_state.gsc_raw_df) if st.session_state.gsc_raw_df is not None else 0)
                        
                except Exception as e:
                    st.error(f"❌ Error processing files: {str(e)}")
    
    # Preview section
    if st.session_state.processed:
        st.divider()
        st.subheader("📋 Data Preview")
        
        tab1, tab2, tab3 = st.tabs(["Links", "GSC Data", "Embeddings"])
        
        with tab1:
            if st.session_state.links_df is not None:
                st.write(f"Showing first 10 of {len(st.session_state.links_df):,} links:")
                st.dataframe(st.session_state.links_df.head(10), use_container_width=True)
        
        with tab2:
            if st.session_state.gsc_raw_df is not None:
                st.write(f"Showing first 10 of {len(st.session_state.gsc_raw_df):,} GSC rows:")
                st.dataframe(st.session_state.gsc_raw_df.head(10), use_container_width=True)
            else:
                st.info("No GSC data uploaded (optional)")
        
        with tab3:
            if st.session_state.embeddings_map:
                st.write(f"Embeddings loaded for {len(st.session_state.embeddings_map)} URLs")
                sample_urls = list(st.session_state.embeddings_map.keys())[:5]
                st.write("Sample URLs with embeddings:")
                for url in sample_urls:
                    st.write(f"• {url}")

# Tab 2: Analyze Links
with tabs[1]:
    st.header("🔍 Analyze Link Opportunities")
    
    if not (st.session_state.embeddings_map and st.session_state.links_df is not None):
        render_warning_box("⚠️ Please upload and process files in the first tab before analyzing.")
    else:
        params = render_analysis_controls()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔗 Find Related Pages", use_container_width=True):
                with st.spinner("Computing semantic similarities..."):
                    related_pages_map = similarity_engine.compute_related_pages(
                        embeddings_map=st.session_state.embeddings_map,
                        top_k=params["top_k_related"]
                    )
                    st.session_state.related_pages_map = related_pages_map
                    st.success(f"✅ Found related pages for {len(related_pages_map)} URLs")
        
        with col2:
            if st.button("🔑 Extract Keywords", use_container_width=True):
                if st.session_state.gsc_raw_df is not None and not st.session_state.gsc_raw_df.empty:
                    with st.spinner("Extracting keywords from GSC data..."):
                        url_keywords_map = gsc_processor.extract_top_keywords_by_url(st.session_state.gsc_raw_df, top_n=3)
                        st.session_state.url_keywords_map = url_keywords_map
                        st.success(f"✅ Extracted keywords for {len(url_keywords_map)} URLs from GSC")
                elif st.session_state.use_ai_for_extraction and ai_client is not None:
                    with st.spinner("Extracting keywords using AI (this may take a moment)..."):
                        url_keywords_map = link_content_generator.ai_extract_keywords_for_urls(
                            list(st.session_state.embeddings_map.keys()), 
                            max_urls=100
                        )
                        st.session_state.url_keywords_map = url_keywords_map
                        st.success(f"✅ AI extracted keywords for {len(url_keywords_map)} URLs")
                else:
                    st.info("💡 Upload GSC data or enable AI extraction to get keyword insights")
                    st.session_state.url_keywords_map = {}
        
        with col3:
            if st.session_state.use_dataforseo and dataforseo_client is not None and st.session_state.url_keywords_map:
                flat_keywords = sorted({kw for kws in st.session_state.url_keywords_map.values() for kw in kws})
                if len(flat_keywords) > 0:
                    batch_count = (len(flat_keywords) - 1) // 1000 + 1
                    if st.button(f"📊 Get Search Volume ({len(flat_keywords)} keywords, {batch_count} {'batch' if batch_count == 1 else 'batches'})", use_container_width=True):
                        with st.spinner(f"Fetching search volumes from DataForSEO..."):
                            try:
                                search_volume_map = dataforseo_client.get_monthly_search_volume(
                                    flat_keywords,
                                    location="US",
                                    language="English"
                                )
                                st.session_state.search_volume_map = {k.lower(): v for k, v in search_volume_map.items()}
                                st.success(f"✅ Retrieved volumes for {len(st.session_state.search_volume_map)} keywords.")
                        except Exception as e:
                            st.error(f"Failed to fetch search volumes: {str(e)}")
        
        st.divider()
        
        # Main analysis button
        if st.button("🎯 Run Full Analysis", type="primary", use_container_width=True):
            if not st.session_state.related_pages_map:
                render_warning_box("⚠️ Please find related pages first!")
            else:
                with st.spinner("Analyzing link opportunities..."):
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
                    st.success(f"✅ Analysis complete! Found opportunities for {len(analysis_df):,} pages")
        
        # Results display
        if st.session_state.analysis_df is not None:
            st.divider()
            st.subheader("📊 Analysis Results")
            
            # Filters
            col1, col2 = st.columns(2)
            with col1:
                priority_filter = st.multiselect(
                    "Filter by Priority",
                    options=["High", "Medium", "Low"],
                    default=["High", "Medium", "Low"]
                )
            
            # Apply filters
            filtered_df = st.session_state.analysis_df
            if "Implementation Priority" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["Implementation Priority"].isin(priority_filter)]
            
            # Display
            st.write(f"Showing {len(filtered_df)} opportunities:")
            st.dataframe(filtered_df.head(100), use_container_width=True)
            
            # Quick export
            col1, col2 = st.columns(2)
            with col1:
                client_prefix = f"{st.session_state.current_client}_" if st.session_state.current_client else ""
                filename = f"{client_prefix}link_analysis.csv"
                if st.button("💾 Export as CSV", use_container_width=True):
                    export_manager.export_df(st.session_state.analysis_df, filename=filename)
            with col2:
                filename = f"{client_prefix}link_analysis.xlsx"
                if st.button("📊 Export as Excel", use_container_width=True):
                    export_manager.export_excel({"Analysis": st.session_state.analysis_df}, filename=filename)

# Tab 3: Generate Content
with tabs[2]:
    st.header("✏️ Generate Link Content")
    
    if not ai_client:
        render_warning_box("⚠️ AI provider required! Configure OpenAI, Anthropic, or Gemini in the sidebar.")
    elif st.session_state.analysis_df is None or st.session_state.related_pages_map is None:
        render_warning_box("⚠️ Please run the analysis first in the Analyze Links tab.")
    else:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            target_urls = sorted(st.session_state.related_pages_map.keys())
            target_url = st.selectbox(
                "Select source page (where link will be placed)",
                options=target_urls,
                help="The page where you'll add the internal link"
            )
        
        with col2:
            suggested_destinations = st.session_state.related_pages_map.get(target_url, [])[:20]
            destination_url = st.selectbox(
                "Select destination page (where link points to)",
                options=suggested_destinations if suggested_destinations else target_urls,
                help="The page you're linking to"
            )
        
        # Show similarity info
        if suggested_destinations:
            st.info(f"💡 These destinations are semantically related to the source page")
        
        # Generate button
        if st.button("✨ Generate Link Suggestion", type="primary", use_container_width=True):
            with st.spinner("AI is crafting the perfect internal link..."):
                try:
                    suggestion = link_content_generator.generate_link_suggestions(
                        target_url=target_url,
                        destination_url=destination_url,
                        gsc_df=st.session_state.gsc_raw_df
                    )
                    
                    # Display suggestion
                    st.success("✅ Link suggestion generated!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Suggested Anchor Text:**")
                        st.code(suggestion.get("anchor_text", ""))
                        
                        st.markdown("**Placement Hint:**")
                        st.write(suggestion.get("placement_hint", ""))
                    
                    with col2:
                        st.markdown("**Content Snippet:**")
                        st.write(suggestion.get("content_snippet", ""))
                        
                        qa = suggestion.get("qa", {})
                        if qa.get("status") == "OK":
                            st.success("✅ Quality check passed")
                        else:
                            st.warning(f"⚠️ {qa.get('notes', '')}")
                    
                    # Save to suggestions
                    row = {
                        "Target URL": target_url,
                        "Destination URL": destination_url,
                        "Anchor Text": suggestion.get("anchor_text", ""),
                        "Placement Hint": suggestion.get("placement_hint", ""),
                        "Content Snippet": suggestion.get("content_snippet", ""),
                        "Status": "Suggested",
                        "Implementation Priority": suggestion.get("priority", 0.5)
                    }
                    st.session_state.suggestions_df = pd.concat(
                        [st.session_state.suggestions_df, pd.DataFrame([row])], 
                        ignore_index=True
                    )
                    
                except Exception as e:
                    st.error(f"❌ Error generating suggestion: {str(e)}")
        
        # Display all suggestions
        if len(st.session_state.suggestions_df) > 0:
            st.divider()
            st.subheader("📝 Generated Suggestions")
            st.write(f"Total suggestions in this session: {len(st.session_state.suggestions_df)}")
            st.dataframe(st.session_state.suggestions_df.tail(50), use_container_width=True)
            
            # Export suggestions
            col1, col2 = st.columns(2)
            with col1:
                client_prefix = f"{st.session_state.current_client}_" if st.session_state.current_client else ""
                if st.button("💾 Export Suggestions CSV", use_container_width=True):
                    export_manager.export_df(
                        st.session_state.suggestions_df, 
                        filename=f"{client_prefix}link_suggestions.csv"
                    )
            with col2:
                if st.button("📊 Export Suggestions Excel", use_container_width=True):
                    export_manager.export_excel(
                        {"Suggestions": st.session_state.suggestions_df}, 
                        filename=f"{client_prefix}link_suggestions.xlsx"
                    )

# Tab 4: Export Results
with tabs[3]:
    st.header("📊 Export All Results")
    
    if st.session_state.current_client:
        st.info(f"📁 Exporting data for: **{st.session_state.current_client}**")
    
    # Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        analysis_count = len(st.session_state.analysis_df) if st.session_state.analysis_df is not None else 0
        st.metric("Analysis Rows", f"{analysis_count:,}")
    with col2:
        suggestions_count = len(st.session_state.suggestions_df)
        st.metric("Generated Suggestions", suggestions_count)
    with col3:
        total_opportunities = analysis_count
        st.metric("Total Opportunities", f"{total_opportunities:,}")
    
    st.divider()
    
    # Export options
    st.subheader("📦 Export Options")
    
    client_prefix = f"{st.session_state.current_client}_" if st.session_state.current_client else ""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📄 Individual Exports")
        
        if st.session_state.analysis_df is not None:
            if st.button("💾 Export Analysis (CSV)", use_container_width=True):
                export_manager.export_df(
                    st.session_state.analysis_df, 
                    filename=f"{client_prefix}analysis.csv"
                )
        
        if len(st.session_state.suggestions_df) > 0:
            if st.button("💾 Export Suggestions (CSV)", use_container_width=True):
                export_manager.export_df(
                    st.session_state.suggestions_df, 
                    filename=f"{client_prefix}suggestions.csv"
                )
    
    with col2:
        st.markdown("### 📦 Bundle Exports")
        
        if st.session_state.analysis_df is not None:
            if st.button("📊 Export All (Excel)", use_container_width=True):
                sheets = {}
                sheets["Analysis"] = st.session_state.analysis_df
                if len(st.session_state.suggestions_df) > 0:
                    sheets["Suggestions"] = st.session_state.suggestions_df
                export_manager.export_excel(
                    sheets, 
                    filename=f"{client_prefix}complete_report.xlsx"
                )
            
            if st.button("🗂️ Export All (ZIP)", use_container_width=True):
                files = {
                    "analysis.csv": st.session_state.analysis_df,
                    "suggestions.csv": st.session_state.suggestions_df
                }
                export_manager.export_zip_csv(
                    files, 
                    filename=f"{client_prefix}all_data.zip"
                )
    
    # Data preview
    if st.session_state.analysis_df is not None or len(st.session_state.suggestions_df) > 0:
        st.divider()
        st.subheader("📋 Data Preview")
        
        tab1, tab2 = st.tabs(["Analysis Results", "Link Suggestions"])
        
        with tab1:
            if st.session_state.analysis_df is not None:
                st.dataframe(st.session_state.analysis_df.head(50), use_container_width=True)
            else:
                st.info("No analysis data yet")
        
        with tab2:
            if len(st.session_state.suggestions_df) > 0:
                st.dataframe(st.session_state.suggestions_df.head(50), use_container_width=True)
            else:
                st.info("No suggestions generated yet")

# Footer
st.divider()
st.caption("🔗 Enhanced Internal Link Opportunity Finder | Multi-Client SEO Tool | File Upload Version")
st.caption("Export GSC data manually and upload as CSV for best results")


