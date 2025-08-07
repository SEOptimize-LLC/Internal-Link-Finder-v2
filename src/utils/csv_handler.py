import pandas as pd
from io import BytesIO, StringIO
from typing import Union

def safe_read_csv(uploaded_file: Union[BytesIO, StringIO, None]) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(uploaded_file, encoding="utf-8")
    except Exception:
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="latin-1")
        except Exception:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, engine="python", on_bad_lines="skip")
