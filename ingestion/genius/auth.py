# ingestion/genius/auth.py
import requests

class GeniusAuthenticator:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session_token = None

    def login(self):
        url = f"{self.base_url}/api/token/"
        payload = {
            "username": self.username,
            "password": self.password
        }

        response = requests.post(url, json=payload)

        # Always show the status and raw text for now
        print("Login status:", response.status_code)
        print("Login response text:")
        print(response.text)

        response.raise_for_status()

        try:
            token = response.json().get("access") 
            print("Received token:", token)
        except Exception as e:
            print("Failed to decode JSON:")
            raise

        self.session_token = token
        return self.session_token



