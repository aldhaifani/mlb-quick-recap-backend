import requests
from typing import Any, Dict, Optional
import logging
from fastapi import HTTPException


logger = logging.getLogger(__name__)

class HTTPClient:
  def __init__(self, base_url: str):
    self.base_url = base_url.rstrip("/")
    self.session = requests.Session()
  
  async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict:
    """"
    Make a GET request to the specified endpoint with optional query parameters.
    """
    try:
      url = f"{self.base_url}/{endpoint.lstrip('/')}"
      response = self.session.get(url, params=params)
      response.raise_for_status()
      return response.json()
    except requests.exceptions.RequestException as e:
      logger.error(f"Error making request to {url}: {str(e)}")
      raise HTTPException(status_code=503, detail="MLB API service unavailable")
    except ValueError as e:
      logger.error(f"Error parsing JSON response from {url}: {str(e)}")
      raise HTTPException(status_code=500, detail="Invalid response from MLB API")