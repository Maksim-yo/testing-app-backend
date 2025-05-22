import requests
import os
CLERK_API_KEY = os.getenv("CLERK_API_KEY")  # безопасно  
CLERK_API_URL = "https://api.clerk.dev/v1"

headers = {
        "Authorization": f"Bearer {CLERK_API_KEY}",
        "Content-Type": "application/json",
    }

url = f"{CLERK_API_URL}/invitations/inv_2x5ZsAg2q2sxMRz8v4jsZuYJDif/revoke"
print(requests.post(url, headers=headers).json())