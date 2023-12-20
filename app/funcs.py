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

from logrr import lm
from config.config import config
from datetime import datetime
import os
import csv
import aiofiles
import json


def get_access_token_from_json():
    token_file_path = config.TOKEN_FILE_PATH
    try:
        with open(token_file_path, 'r') as file:
            # Check if the file is empty
            if file.read(1):
                file.seek(0)  # Reset file read position
                token = json.load(file)
                lm.display_json_as_rich_table(token, title='Token')
            else:
                raise ValueError("Token file is empty.")
        return token
    except FileNotFoundError:
        lm.log_and_print(f"Token file not found at path: {token_file_path}", style="error", level="error")
        return None
    except json.JSONDecodeError:
        lm.log_and_print(f"Invalid JSON format in token file at {token_file_path}", style="error", level="error")
        return None
    except ValueError as ve:
        lm.log_and_print(str(ve), style="error", level="error")
        return None
    except Exception as e:
        lm.log_and_print(f"Unexpected error while reading token file: {e}", style="error", level="error")
        return None


async def save_access_token_to_json(token):
    token_file_path = config.TOKEN_FILE_PATH  # Assumes token.json is the intended file

    try:
        # Convert token to JSON string
        json_data = json.dumps(token, indent=4)
        # lm.log_and_print('Access token successfully convert to JSON')
    except (TypeError, OverflowError) as json_error:
        lm.log_and_print(f"Error converting token to JSON: {json_error}", level="error")
        return False

    try:
        # Async write the token dictionary to tokens.json file
        async with aiofiles.open(token_file_path, 'w') as file:
            await file.write(json_data)
        lm.log_and_print(f"Access token successfully saved to {token_file_path}", style="success")
        return True
    except IOError as io_error:
        lm.log_and_print(f"IO error while saving token to file: {io_error}", level="error")
        return False
    except Exception as e:
        lm.log_and_print(f"Unexpected error while saving token: {e}", level="error")
        return False


def is_token_expired(token):
    """Check if the token is expired."""
    try:
        # If 'expires_at' key is missing or invalid, this will raise an error
        return datetime.now().timestamp() > token.get('expires_at', 0)
    except Exception as e:
        lm.log_and_print(f"Error checking token expiration: {e}", style="error", level="error")
        return True  # Assume the token is expired if an error occurs


def is_refresh_token_expired(token):
    """Check if the refresh token is expired."""
    try:
        refresh_token_lifespan = token.get('refresh_token_expires_in', 0)  # lifespan in seconds
        token_acquired_time = token.get('acquired_at', datetime.now().timestamp())  # Time when the token was saved
        refresh_token_expiry_time = token_acquired_time + refresh_token_lifespan
        return datetime.now().timestamp() > refresh_token_expiry_time
    except Exception as e:
        lm.log_and_print(f"Error checking refresh token expiration: {e}", style="error", level="error")
        return True  # Assume the refresh token is expired if an error occurs


def write_to_csv(data):
    try:
        # Check if data is empty or None
        if not data:
            raise ValueError("No data provided to write to CSV.")

        # Define the directory for CSV files using the Config class
        folder_name = config.CSV_FILE_PATH
        base_filename = 'cdr_output'

        # Check if the directory exists, and create it if it does not
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        # Append the current date/time to the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{folder_name}/{base_filename}_{timestamp}.csv"

        with open(filename, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=data[0].keys())
            writer.writeheader()
            for row in data:
                writer.writerow(row)

        lm.console.print(f"Data successfully written to {filename}")

    except ValueError as ve:
        lm.log_and_print(f"CSV Writing Error: {ve}", style="error", level="error")

    except Exception as e:
        lm.log_and_print(f"Unexpected error while writing to CSV: {e}", style="error", level="error")
