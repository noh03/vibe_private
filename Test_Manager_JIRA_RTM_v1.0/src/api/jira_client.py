import requests
import logging
from typing import Dict, Any, Optional

class JiraRTMClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.logger = logging.getLogger(__name__)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        try:
            response.raise_for_status()
            if not response.text:
                return {}
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP Error: {e} - Body: {response.text}")
            raise
        except Exception as e:
            self.logger.error(f"Request Error: {e}")
            raise

    def test_connection(self) -> bool:
        """Verify connection by checking current user"""
        try:
            self._handle_response(requests.get(f"{self.base_url}/rest/api/2/myself", headers=self.headers))
            return True
        except Exception:
            return False

    def get_tree_structure(self, project_id: int = 41500) -> Dict[str, Any]:
        """Fetch the RTM Tree Structure"""
        endpoint = f"/rest/rtm/1.0/api/tree/{project_id}"
        url = f"{self.base_url}{endpoint}"
        return self._handle_response(requests.get(url, headers=self.headers))

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get standard JIRA issue details"""
        endpoint = f"/rest/api/2/issue/{issue_key}"
        url = f"{self.base_url}{endpoint}"
        return self._handle_response(requests.get(url, headers=self.headers))

    def create_rtm_issue(self, project_id: str, issue_type: str, summary: str, description: str = "") -> Dict[str, Any]:
        """Create an issue via Standard JIRA API"""
        endpoint = "/rest/api/2/issue"
        url = f"{self.base_url}{endpoint}"
        
        payload = {
            "fields": {
                "project": {"id": project_id},
                "issuetype": {"name": issue_type},
                "summary": summary,
                "description": description
            }
        }
        return self._handle_response(requests.post(url, headers=self.headers, json=payload))

