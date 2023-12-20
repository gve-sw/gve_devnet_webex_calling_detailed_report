import pathlib
import re
from typing import Optional, ClassVar, List, Dict, Any
from dotenv import load_dotenv
from pydantic import field_validator, model_validator, validator, root_validator
from pydantic_settings import BaseSettings
import json
from datetime import datetime

# Adjust the path to load the .env file from the project root.
env_path = pathlib.Path(__file__).parents[0] / '.env'
# print(f'env path: {env_path}')  # for debugging
load_dotenv(dotenv_path=env_path)


class Config(BaseSettings):
    # DIR PATHS
    DIR_PATH: ClassVar[pathlib.Path] = pathlib.Path(__file__).parents[2]
    ENV_FILE_PATH: ClassVar[str] = str(DIR_PATH / 'app' / 'config' / '.env')
    TOKEN_FILE_PATH: ClassVar[str] = str(DIR_PATH / 'app' / 'data' / 'token.json')
    CSV_FILE_PATH: ClassVar[str] = str(DIR_PATH / 'app' / 'data')
    README_PATH: ClassVar[str] = str(DIR_PATH / 'README.md')

    # Flask Settings
    APP_NAME: Optional[str] = 'Update your app name in .env'
    APP_VERSION: Optional[str] = 'Update your ap'
    DEV_ENV: Optional[str] = 'development'
    IS_PRODUCTION: bool = DEV_ENV.lower() == 'production'  # True if FLASK_ENV is "production," otherwise False
    LOGGER_LEVEL: str = 'DEBUG'
    UVICORN_LOG_LEVEL: str = 'WARNING'

    # Webex Integration settings
    AUTHORIZATION_BASE_URL: str
    TOKEN_URL: str
    # FULL_WEBEX_OAUTH_TOKEN: Optional[str] = None
    # WEBEX_ACCESS_TOKEN: Optional[str] = None
    CLIENT_ID: str
    CLIENT_SECRET: str
    SCOPE: str
    PUBLIC_URL: str
    WEBEX_BASE_URL: str

    NUMBER_OF_DAYS_CDR_REPORT: Optional[int]
    START_DATE: Optional[str]
    END_DATE: Optional[str]

    _instance: ClassVar[Optional['Config']] = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @model_validator(mode='before')
    def validate_dates(cls, data: dict):
        start_date_str = data.get('START_DATE')
        end_date_str = data.get('END_DATE')
        if not (start_date_str and end_date_str):
            return data

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        if end_date < start_date:
            raise ValueError("END_DATE cannot be earlier than START_DATE")
        if (end_date - start_date).days > 30:
            raise ValueError("Date range should not exceed 30 days")
        return data

    @model_validator(mode='before')
    def parse_metrics(cls, values):
        metrics_json = values.get('METRICS_JSON')
        if metrics_json:
            try:
                values['METRICS'] = json.loads(metrics_json)
            except json.JSONDecodeError:
                raise ValueError('METRICS_JSON is not a valid JSON string')
        return values

    @field_validator('LOGGER_LEVEL', mode='before')
    def set_logger_level(cls, v):
        # Check if LOGGER_LEVEL is empty or None, default to 'DEBUG'
        if not v:
            return 'DEBUG'
        return v.upper()

    @field_validator('NUMBER_OF_DAYS_CDR_REPORT', mode='before')
    def validate_number_of_days_for_cdr_report(cls, v):
        # If the value is an empty string, treat it as None
        if v == '':
            return None
        # Allow None or 0 to pass through without validation
        if v is None or v == 0:
            return v
        try:
            v = int(v)
        except ValueError:
            raise ValueError("NUMBER_OF_DAYS_CDR_REPORT must be an integer")
        if not 1 <= v <= 31:
            raise ValueError("NUMBER_OF_DAYS_CDR_REPORT must be an integer between 1 and 31")
        return v

    @field_validator('PUBLIC_URL', mode='before')
    def validate_public_url(cls, v):
        if not v:
            raise ValueError('PUBLIC_URL must not be empty')
        return v

    @field_validator('AUTHORIZATION_BASE_URL', mode='before')
    def validate_authorization_base_url(cls, v):
        if not re.match(r'https://api\.ciscospark\.com/v1/authorize', v):
            raise ValueError('AUTHORIZATION_BASE_URL must be https://api.ciscospark.com/v1/authorize')
        return v

    @field_validator('TOKEN_URL', mode='before')
    def validate_access_token_url(cls, v):
        if not re.match(r'https://api\.ciscospark\.com/v1/access_token', v):
            raise ValueError('TOKEN_URL must be https://api.ciscospark.com/v1/access_token')
        return v

    @field_validator('WEBEX_BASE_URL', mode='before')
    def validate_webex_base_url(cls, v):
        if not re.match(r'https://webexapis\.com/v1/', v):
            raise ValueError('WEBEX_BASE_URL must be: https://webexapis.com/v1/')
        return v


config = Config.get_instance()
