import os
import requests
import enum
from requests.exceptions import HTTPError
from schemas import EmployeeCreate, ClerkUserCreate, ClerkPublicMetadata, ClerkMetadata, ClerkRole

CLERK_ISSUER = "https://probable-egret-34.clerk.accounts.dev"
JWKS_URL = f"{CLERK_ISSUER}/.well-known/jwks.json"
CLERK_API_KEY = os.getenv("CLERK_API_KEY")  # безопасно
CLERK_API_URL = "https://api.clerk.dev/v1"
jwks_cache = {}
def create_clerk_user(
    first_name: str,
    last_name: str,
    is_admin: bool = False,
    password: str | None = None,
    username: str | None = None,
    email: str | None = None,

):
    role = ClerkRole.ADMIN if is_admin else ClerkRole.EMPLOYEE

    user_data = {
        "first_name": first_name,
        "last_name": last_name,
        "unsafe_metadata": {
            "role": role,
            "is_admin": is_admin,
        },
        "public_metadata": {
            "user_type": role
        }
    }

    if email:
        user_data["email_address"] = [email]

    if password:
        user_data["password"] = password
    if username:
        user_data["username"] = username

    headers = {
        "Authorization": f"Bearer {CLERK_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{CLERK_API_URL}/users",
        headers=headers,
        json=user_data
    )
    response.raise_for_status()
    return response.json()




def delete_clerk_user(clerk_id: str):
    headers = {
        "Authorization": f"Bearer {CLERK_API_KEY}",
        "Content-Type": "application/json",
    }
    if clerk_id.startswith("user_"):
        print(f"Deleting registered user: {clerk_id}")
        user_response = requests.delete(f"{CLERK_API_URL}/users/{clerk_id}", headers=headers)
        if user_response.status_code == 200:
            return user_response.json()
        else:
            user_response.raise_for_status()

    elif clerk_id.startswith("inv_"):
        print(f"Deleting invitation: {clerk_id}")
        inv_response = requests.post(f"{CLERK_API_URL}/invitations/{clerk_id}/revoke", headers=headers)
        if inv_response.status_code in (200, 204):
            return inv_response.json()
        elif inv_response.status_code == 404:
            print(f"Invitation {clerk_id} not found.")
            return None
        else:
            inv_response.raise_for_status()

    else:
        raise Exception("Invalid clerk_id format")


def update_clerk_user(employee_data: EmployeeCreate, clerk_id: str):
    headers = {
        "Authorization": f"Bearer {CLERK_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {}

    if employee_data.first_name:
        data["first_name"] = employee_data.first_name
    if employee_data.last_name:
        data["last_name"] = employee_data.last_name
    if employee_data.email:
        data["email_address"] = employee_data.email
    # if employee_data.role:
        # data["public_metadata"] = {"role": employee_data.}

    response = requests.patch(f"{CLERK_API_URL}/users/{clerk_id}", headers=headers, json=data)

    if response.status_code == 200:
        return response.json()  
    else:
        response.raise_for_status()  
