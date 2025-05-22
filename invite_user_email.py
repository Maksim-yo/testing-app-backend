import requests
from auth import CLERK_API_KEY

def invite_user_via_clerk(email: str, redirect_url: str):
    headers = {
        "Authorization": f"Bearer {CLERK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "email_address": email,
        "redirect_url": redirect_url,  # URL, куда пользователь попадет после клика
    }

    response = requests.post(
        "https://api.clerk.dev/v1/invitations",
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    return response.json()


def cancel_invitation(invitation_id: str):
    headers = {
        "Authorization": f"Bearer {CLERK_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.delete(
        f"https://api.clerk.dev/v1/invitations/{invitation_id}",
        headers=headers,
    )

    response.raise_for_status()  # Если статус не 2xx, поднимет исключение

    return response.json()