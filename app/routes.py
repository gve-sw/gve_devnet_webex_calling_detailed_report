"""
Copyright (c) 2023 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at https://developer.cisco.com/docs/licenses.
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from requests_oauthlib import OAuth2Session

from config.config import config
from logrr import lm
from funcs import get_access_token_from_json, save_access_token_to_json, is_token_expired, is_refresh_token_expired
from webex_cdr_processor import CDRReportProcessor

# Importing constants/load config settings
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET
SCOPE = config.SCOPE.split(',')  # Convert the comma-separated string to a list
PUBLIC_URL = config.PUBLIC_URL
AUTHORIZATION_BASE_URL = config.AUTHORIZATION_BASE_URL
TOKEN_URL = config.TOKEN_URL
REDIRECT_URI = PUBLIC_URL + '/callback'

webex_router = APIRouter()
templates = Jinja2Templates(directory="templates")


# FastAPI endpoints

# Define a single async function to handle multiple routes
async def homepage(request: Request):
    return templates.TemplateResponse(name='home.html', context={'request': request})


@webex_router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return await homepage(request)


@webex_router.get("/index", response_class=HTMLResponse)
async def index(request: Request):
    return await homepage(request)


@webex_router.get("/complete", response_class=HTMLResponse)
async def complete(request: Request):
    return templates.TemplateResponse(name='complete.html', context={'request': request})


@webex_router.get("/oauth_success", response_class=HTMLResponse)
async def complete(request: Request):
    return templates.TemplateResponse(name='oauth_success.html', context={'request': request})



@webex_router.get("/login")
async def login():
    token = get_access_token_from_json()
    if token:
        if is_refresh_token_expired(token):
            return RedirectResponse(url="/start_oauth")
        elif is_token_expired(token):
            return RedirectResponse(url="/refresh_token")
        else:
            return RedirectResponse(url="/oauth_success")
    else:
        return RedirectResponse(url="/start_oauth")


@webex_router.get("/start_oauth")
async def start_oauth():
    try:
        lm.p_panel('[bright_white]1. Initiating OAuth flow for user authentication with Webex.[/bright_white]', style='webex', expand=False)
        auth_client = OAuth2Session(CLIENT_ID, scope=SCOPE, redirect_uri=REDIRECT_URI)
        authorization_url, state = auth_client.authorization_url(AUTHORIZATION_BASE_URL)
        response = RedirectResponse(url=authorization_url)
        response.set_cookie(key="oauth_state", value=state)  # Using cookies
        lm.p_panel('[bright_white]2. OAuth flow started. Redirecting to Webex authorization URL.[/bright_white]', style='webex', expand=False)
        return response
    except Exception as e:
        lm.log_and_print(f'Error during OAuth start: {e}', style='error', level='error')
        return RedirectResponse(url="/error")  # Redirect to an error page or handle error differently


@webex_router.get("/callback")
async def callback(request: Request):
    try:
        state = request.cookies.get("oauth_state")
        auth_client = OAuth2Session(CLIENT_ID, state=state, redirect_uri=REDIRECT_URI)
        lm.p_panel('[bright_white]3. Received OAuth callback. Attempting to fetch access token...[/bright_white]', style='webex', expand=False)
        token = auth_client.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=str(request.url))
        if token:
            lm.p_panel('[bright_white]Access token successfully obtained', style='webex', expand=False)
            await save_access_token_to_json(token)
            return RedirectResponse(url="/run_report")
        else:
            lm.p_panel('[bright_white]Failed to obtain access token in OAuth callback.', style='error', expand=False)
            return RedirectResponse(url="/error")
    except Exception as e:
        lm.log_and_print(f'Error in OAuth callback: {e}', style='error', level='error')
        return RedirectResponse(url="/error")


@webex_router.get("/run_report")
async def run_report():
    token = get_access_token_from_json()
    if token:
        try:
            cdr_processor = CDRReportProcessor(token.get('access_token'))
            cdr_processor.run_report()       # Run the report
            return RedirectResponse(url="/complete")
        except Exception as e:
            lm.log_and_print(f'Error running report: {e}', style='error', level='error')
            return RedirectResponse(url="/error")
    else:
        return RedirectResponse(url="/login")       # Redirect to the login flow if token is None


@webex_router.get("/refresh_token")
async def refresh_token():
    token = get_access_token_from_json()
    lm.log_and_print('Starting token refresh process...', style='webex')
    if token and 'refresh_token' in token:
        # try:
        lm.log_and_print('Refreshing access token...', style='webex')

        auth_client = OAuth2Session(CLIENT_ID, token=token)
        new_token = auth_client.refresh_token(TOKEN_URL, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        await save_access_token_to_json(new_token)
        return RedirectResponse(url="/run_report")
    else:
        return RedirectResponse(url="/start_oauth")

