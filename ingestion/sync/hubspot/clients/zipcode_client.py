"""
Client for fetching zip code CSV from GitHub for HubSpot integration
Follows import_refactoring.md enterprise architecture standards
"""
import os
import requests


class HubSpotZipCodeClient:
    def __init__(self, github_token=None, owner=None, repo=None, file_path=None, branch=None):
        self.github_token = (
            github_token
            or os.environ.get("ZIPCODES_GITHUB_TOKEN")
            or os.environ.get("GITHUB_TOKEN")
        )
        self.owner = (
            owner
            or os.environ.get("ZIPCODES_OWNER")
            or "Home-Genius-Exteriors"
        )
        self.repo = (
            repo
            or os.environ.get("ZIPCODES_REPO")
            or "Zipcodes"
        )
        self.file_path = file_path or "zips.csv"
        self.branch = (
            branch
            or os.environ.get("ZIPCODES_BRANCH")
            or "main"
        )

    def fetch_csv(self):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{self.file_path}?ref={self.branch}"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3.raw"
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch CSV: {response.status_code} {response.text}")
        return response.text
