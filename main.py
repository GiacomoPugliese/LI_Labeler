from fastapi import FastAPI
from google_auth_oauthlib.flow import Flow
from fastapi.responses import RedirectResponse
import secrets

app = FastAPI()

tokens = {}  # A simple in-memory storage for tokens

@app.get("/auth")
def auth(user_id: str):
    # Create the Flow instance
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=['https://www.googleapis.com/auth/drive'],
        redirect_uri='https://photo-labeler-842ac8d73e7a.herokuapp.com/callback' # update this with your redirect_uri
    )

    # Set the state for CSRF protection
    flow.state = secrets.token_hex(16)

    # Get the authorization URL for the consent screen
    authorization_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

    # Save the user_id and Flow instance for later
    tokens[0] = {"user_id": user_id, "flow": flow}
    print(f"Auth endpoint: State is {flow.state}")
    print(f"Auth endpoint: Tokens are {tokens}")
    # Return the authorization URL in the response
    return {"authorization_url": authorization_url}


@app.get("/callback")
async def callback(code: str, state: str):
    print(f"Callback endpoint: State is {state}")
    print(f"Callback endpoint: Tokens are {tokens}")
    # Get the saved flow instance
    flow = tokens[0]["flow"]
    flow.fetch_token(code=code)

    credentials = flow.credentials

    # Store the credentials
    tokens[0]["token"] = credentials.token
    tokens[0]["creds"] = credentials
    return "Authentication successful. Please close this window and click 'Finalize Google Authentication'"

@app.get("/token/{user_id}")
async def get_token(user_id: str):
    # Retrieve token using user_id
    return {"creds": tokens[0]["creds"]}
