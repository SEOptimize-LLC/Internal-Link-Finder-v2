# Enhanced Internal Link Opportunity Finder

Streamlit app to detect internal linking opportunities, integrate GSC performance data, enrich with DataForSEO monthly search volumes, and generate link content suggestions with optional AI (OpenAI, Anthropic, Gemini). Exports to CSV/XLSX or Google Sheets.

Quick Start
- Python 3.9+ recommended
- pip install -r requirements.txt
- Copy secrets.template.toml to .streamlit/secrets.toml and fill credentials
- streamlit run app.py
- Deploy to Streamlit Cloud and paste secrets in the Secrets UI

Notes
- GSC API: Add your service account to the Search Console property with read access.
- Google Sheets export: Use a separate service account under [sheets]; created spreadsheets will be owned by that account. Share as needed from Google Drive.
- AI: Choose a provider and model in the sidebar. AI is optional; app runs without it.
