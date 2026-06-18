import json
import time
import urllib.parse
import urllib.request


AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/activities"


def build_authorization_url(client_id, redirect_uri="http://localhost", scope="activity:write"):
    if not str(client_id).strip():
        raise RuntimeError("Strava client ID is required.")

    query = urllib.parse.urlencode(
        {
            "client_id": str(client_id).strip(),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "approval_prompt": "auto",
            "scope": scope,
        }
    )
    return f"{AUTH_URL}?{query}"


def exchange_code(client_id, client_secret, code):
    payload = {
        "client_id": str(client_id).strip(),
        "client_secret": str(client_secret).strip(),
        "code": str(code).strip(),
        "grant_type": "authorization_code",
    }
    return _post_form(TOKEN_URL, payload)


def refresh_access_token(client_id, client_secret, refresh_token):
    payload = {
        "client_id": str(client_id).strip(),
        "client_secret": str(client_secret).strip(),
        "refresh_token": str(refresh_token).strip(),
        "grant_type": "refresh_token",
    }
    return _post_form(TOKEN_URL, payload)


def ensure_access_token(strava_config):
    access_token = strava_config.get("access_token", "")
    expires_at = int(strava_config.get("expires_at", 0) or 0)
    if access_token and expires_at > int(time.time()) + 60:
        return access_token, None

    token = refresh_access_token(
        strava_config.get("client_id", ""),
        strava_config.get("client_secret", ""),
        strava_config.get("refresh_token", ""),
    )
    return token.get("access_token", ""), token


def upload_activity(strava_config, session):
    access_token, updated_token = ensure_access_token(strava_config)
    if not access_token:
        raise RuntimeError("No valid Strava access token. Authorize Strava first.")

    payload = {
        "name": session.get("name", "Maratron Treadmill Session"),
        "type": session.get("activity_type") or strava_config.get("activity_type", "Walk") or "Walk",
        "start_date_local": session["start_date_local"],
        "elapsed_time": int(max(1, session.get("elapsed_time", 0))),
        "distance": float(max(0.0, session.get("distance_m", 0.0))),
        "description": session.get("description", "Uploaded from MaratronVR"),
    }

    if session.get("calories", 0.0) > 0:
        payload["calories"] = int(round(session["calories"]))

    body = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        ACTIVITIES_URL,
        data=body,
        headers={"Authorization": f"Bearer {access_token}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result, updated_token


def _post_form(url, payload):
    body = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))