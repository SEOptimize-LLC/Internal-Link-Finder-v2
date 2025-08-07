import pandas as pd
from io import BytesIO, StringIO
from typing import Union

def safe_read_csv(uploaded_file: Union[BytesIO, StringIO, None]) -> pd.DataFrame:
    """Read CSV or Excel files safely"""
    if uploaded_file is None:
        return pd.DataFrame()
    
    # Get the file name to determine type
    file_name = getattr(uploaded_file, 'name', '')
    
    # Handle Excel files
    if file_name.endswith(('.xlsx', '.xls')):
        try:
            # Read Excel file
            df = pd.read_excel(uploaded_file, engine='openpyxl' if file_name.endswith('.xlsx') else None)
            return df
        except Exception as e:
            # Try reading without specifying engine
            try:
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file)
                return df
            except Exception:
                # If Excel fails, try as CSV (in case of wrong extension)
                uploaded_file.seek(0)
                return safe_read_csv_fallback(uploaded_file)
    
    # Handle CSV files
    return safe_read_csv_fallback(uploaded_file)

def safe_read_csv_fallback(uploaded_file):
    """Fallback CSV reader with multiple encoding attempts"""
    try:
        return pd.read_csv(uploaded_file, encoding="utf-8")
    except Exception:
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="latin-1")
        except Exception:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, engine="python", on_bad_lines="skip")
