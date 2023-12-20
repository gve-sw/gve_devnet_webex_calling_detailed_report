"""
Copyright (c) 2023 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

from fastapi import FastAPI
import uvicorn
from routes import webex_router
from config.config import config
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from logrr import lm

def create_app() -> FastAPI:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Allows use of localhost for testing Oauth flow

    fastapi_app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION)

    # Add CORS middleware
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For development, use ["*"]. For production, specify your frontend's domain
        allow_credentials=True,
        allow_methods=["*"],  # Specifies the methods (GET, POST, etc.) allowed
        allow_headers=["*"],  # Allows all headers
    )

    @fastapi_app.on_event("startup")
    async def on_startup():
        lm.print_start_layout()
        # lm.debug_inspect(config)

        # Serve static files
        fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")

    @fastapi_app.on_event("shutdown")
    async def on_shutdown():
        lm.print_exit_panel()

    # Include routers from different modules
    fastapi_app.include_router(webex_router)

    # handler = Mangum(fastapi_app)     # For AWS
    return fastapi_app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="critical", reload=True)


