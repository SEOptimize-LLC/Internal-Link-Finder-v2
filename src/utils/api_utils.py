import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_retry_session(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504)):
    session = requests.Session()
    retries = Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
