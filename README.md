# gve_devnet_webex_calling_detailed_report
This solution harnesses the Webex Calling APIs to generate in-depth calling reports, exporting the data to CSV for further analysis. 
Designed to enhance organizational productivity and communication efficiency, it focuses on the detailed analysis and visualization of Call Detail Record (CDR) data.

## Contacts
* Mark Orszycki

## Solution Overview
### Key Features and Functionalities:
- **Webex Calling APIs**: Harnesses the power of Webex Calling APIs to fetch detailed call reports, crucial for data-driven decision-making.
- **Automated CSV Output**: Processes and outputs the CDR report into a CSV format, which can be readily used with Microsoft Power BI for enhanced analytics and visualization.
- **OAuth2 Flow with Refresh Tokens**: Implements an OAuth2 authentication flow using FastAPI and Uvicorn, ensuring secure user authentication and continuous access through refresh tokens.
- **Seamless User Authentication**: Allows new users to authenticate with Webex Teams and manages locally stored authentication tokens. For returning users, it checks for existing tokens, automatically refreshing them if needed, or reinitiating the OAuth flow if the refresh token has expired.
- **Detailed Report Generation**: Upon successful authentication, the application runs a detailed Webex calling report, saving the data to a CSV file for subsequent analysis and reporting.

### Key Components
- **Webex Calling REST API**: Central to fetching detailed call data and metrics from Webex, serving as the primary data source for the reports.
- **Python**: The primary programming language for the application.
- **FastAPI**: A modern, high-performance web framework for building APIs with Python, used here for creating the web interface and managing API requests and responses.
- **Uvicorn**: An efficient ASGI server implementation for Python, responsible for running the FastAPI application with excellent performance and concurrency handling.
- **Jinja2**: A powerful template engine for Python, employed to render dynamic HTML templates, for consistent application user interface.
- **HTML & CSS**: HTML provides the structure for web pages, while CSS is used for layout and design.


## Prerequisites
### Webex Prerequisites 
**Webex API Access Token**:
1. To use the Webex REST API, you need a Webex account backed by Cisco Webex Common Identity (CI). If you already have a Webex account, you're all set. Otherwise, go ahead and [sign up for a Webex account](https://cart.webex.com/sign-up).
2. When making request to the Webex REST API, the request must contain a header that includes the access token. A personal access token can be obtained [here](https://developer.webex.com/docs/getting-started).
3. For development and demo purposes, retrieve Webex Access Token and enter it in .env under "WEBEX_ACCESS_TOKEN."
4. See OAuth Integrations section for deployment details outside of development.
> Note: Use of OAuth integration is necessary as PAT has a short lifetime - only 12 hours after logging into this site - so it shouldn't be used outside of app development.

**OAuth Integrations**: 
1. Integrations are how you request permission to invoke the Webex REST API on behalf of another Webex Teams user. To do this in a secure way, the API supports the OAuth2 standard which allows third-party integrations to get a temporary access token for authenticating API calls instead of asking users for their password. To register an integration with Webex Teams:
2. Log in to `developer.webex.com`
3. Click on your avatar at the top of the page and then select `My Webex Apps`
4. Click `Create a New App`
5. Click `Create an Integration` to start the wizard
6. Follow the instructions of the wizard and provide your integration's name, description, and logo
7. After successful registration, you'll be taken to a different screen containing your integration's newly created Client ID and Client Secret
8. Copy the secret and store it safely. Please note that the Client Secret will only be shown once for security purposes
9. Note that access token may not include all the scopes necessary for this prototype by default. To include the necessary scopes, select `My Webex Apps` under your avatar once again. Then click on the name of the integration you just created. Scroll down to the `Scopes` section. From there, select all the scopes needed for this integration.
10. To read more about Webex Integrations & Authorization and to find information about the different scopes, you can find information [here](https://developer.webex.com/docs/integrations)

*Webex Token Management:*
> Access Token (14 days): Used for authenticating API requests. Checked for validity and refreshed as needed.
> Refresh Token (90 days): Used to obtain a new access token when the current one expires. Checked for its expiry and triggers re-authentication if expired.

### Required Scopes:
The following scopes are required for this application. Save in .env:
```script
SCOPE=spark:all,spark-admin:calling_cdr_read,analytics:read_all
```


## Installation/Configuration
1. Clone this repository with `git clone https://github.com/gve-sw/gve_devnet_webex_calling_detailed_report.git`
2. Set up a Python virtual environment. Make sure Python 3 is installed in your environment, and if not, you may download Python [here](https://www.python.org/downloads/). Once Python 3 is installed in your environment, you can activate the virtual environment with the instructions found [here](https://docs.python.org/3/tutorial/venv.html).
3. Install the requirements into virtual environment with 'pip3 install -r requirements.txt'

### Create .env
1. Create .env in app/config/:
```script
cd app/config
touch .env
open .env
```
### Steps to Update the `.env` File:
To configure the application, you need to update the `.env` file with the appropriate values. 
This file contains key settings that the application uses to interact with the Webex APIs and to set up its environment.
1. **Set the Application Details**:
   - `APP_NAME`: Name of your application (e.g., "Webex CDR Productivity Report").
   - `APP_VERSION`: The current version of your application (e.g., "1.0").

2. **Configure Environment and Logging**:
   - `DEV_ENV`: Set to `production` or `development` based on your environment.
   - `LOGGER_LEVEL`: Set the logging level (e.g., `DEBUG`).

3. **Webex API Configuration**:
   - `AUTHORIZATION_BASE_URL`: URL for Webex authorization ("https://api.ciscospark.com/v1/authorize").
   - `TOKEN_URL`: URL to obtain access tokens ("https://api.ciscospark.com/v1/access_token").
   - `WEBEX_BASE_URL`: Base URL for Webex API ("https://webexapis.com/v1/").

4. **Client ID and Secret**:
   - `CLIENT_ID`: Your Webex Integration Client ID.
   - `CLIENT_SECRET`: Your Webex Integration Client Secret.

5. **Specify the Scope and Public URL**:
   - `SCOPE`: The required scope of access ("spark:all,analytics:read_all,spark-admin:calling_cdr_read").
   - `PUBLIC_URL`: The public URL of your application ("http://127.0.0.1:8000").

6. **Report Configuration**:
   - `NUMBER_OF_DAYS_CDR_REPORT`: Define a specific number of days for the CDR report (leave blank to use date range).
   - `START_DATE` and `END_DATE`: Specify the start and end dates for the report (format: YYYY-MM-DD).

### Note:
- Ensure that the `CLIENT_ID` and `CLIENT_SECRET` are obtained from your Webex Integration setup.
- The date range for `START_DATE` and `END_DATE` should not exceed 31 days.
- Ensure the following variables match exactly as in the example below: AUTHORIZATION_BASE_URL, TOKEN_URL, SCOPE,

Once you have updated and saved the `.env` file with the correct values, the application will be configured to run with these settings.

Example `.env`:
```
APP_NAME="Webex CDR Productivity Report"
APP_VERSION="1.0"
DEV_ENV=development
LOGGER_LEVEL=DEBUG
AUTHORIZATION_BASE_URL="https://api.ciscospark.com/v1/authorize"
TOKEN_URL="https://api.ciscospark.com/v1/access_token"
WEBEX_BASE_URL="https://webexapis.com/v1/"
CLIENT_ID=YOUR_WEBEX_INTEGRATION_CLIENT_ID
CLIENT_SECRET=YOUR_WEBEX_INTEGRATION_CLIENT_SECRET
SCOPE=spark:all,analytics:read_all,spark-admin:calling_cdr_read
PUBLIC_URL=http://127.0.0.1:8000
NUMBER_OF_DAYS_CDR_REPORT=
START_DATE=2023-10-16
END_DATE=2023-11-13
```

## Usage
### Start the Application
To initiate the prototype, start the FastAPI application:
```
$ cd app
$ uvicorn main:app --reload 
```

### Accessing the Application
After starting the server, access the application by navigating to the PUBLIC_URL in your web browser. 
It's recommended to use an incognito window to prevent potential issues with cookies or session data.

### Running the Webex Calling Detailed Report
After successful user authentication, the application initiates the Webex Calling Detailed Report. 
This process involves several stages and can take 5-10+ minutes, depending on various factors like data volume and server response times.

#### What to Expect:
- **Browser Loading**: During report generation, the browser will indicate a "loading" state. This is normal as the application is actively working on fetching and compiling the report data.
- **Backend Process**: In the backend, you will observe messages such as "fetching cdr report". This signifies that the application is querying and waiting for the report to complete. It will display the various stages of fetching the report of detailed call records from Webex.
- **Completion and Output**: Once the report is fully fetched and processed, it will be outputted to a CSV file under `app/data/`. This file will contain the detailed call data, which you can then review or use as needed.

#### Please Note:
- **Patience is Key**: Due to the nature of data processing and retrieval from Webex, the report generation might take longer than usual. It's important to allow the process to complete without interruption.
- **Browser Behavior**: While the browser remains in the "loading" state, avoid refreshing or closing the tab to ensure uninterrupted report generation.


## Additional Info
### Screenshots
Start:
![/IMAGES/console1.png](/IMAGES/console1.png)<br>

Webex Authentication:
![/IMAGES/console2.png](/IMAGES/console2.png)<br>

Webex Report List:
![/IMAGES/console3.png](/IMAGES/console3.png)<br>

Run the report:
![/IMAGES/console4.png](/IMAGES/console4.png)<br>

Frontend:
![/IMAGES/frontend1.png](/IMAGES/frontend1.png)<br>
![/IMAGES/frontend2.png](/IMAGES/frontend2.png)<br><br>

![/IMAGES/0image.png](/IMAGES/0image.png)


### Configuration for OAuth Flow
For local testing, line 12 in main.py enables OAuth flows with localhost: `os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'`
Note for Production: This setting must be removed for production environments. 
Secure HTTPS endpoints, typically involving a registered domain and SSL/TLS setup,
are required for production deployments to ensure data security and user privacy.

### Token Management
Tokens (authentication and refresh) are stored in tokens.json, allowing continuous application use without constant reauthentication. 
Tokens auto-refresh every 60 days during normal use, or manually via the /refresh_token route.

### Security Note
While tokens.json is convenient for development, it should be emptied post-use to secure data. 
For production, replace this with a more secure storage method (e.g., encrypted database or secret management service) 
to safeguard token integrity and comply with security best practices.


### LICENSE
Provided under Cisco Sample Code License, for details see [LICENSE](LICENSE.md)

### CODE_OF_CONDUCT
Our code of conduct is available [here](CODE_OF_CONDUCT.md)

### CONTRIBUTING
See our contributing guidelines [here](CONTRIBUTING.md)

#### DISCLAIMER:
<b>Please note:</b> This script is meant for demo purposes only. All tools/ scripts in this repo are released for use 
"AS IS" without any warranties of any kind, including, but not limited to their installation, use, or performance.
Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough 
testing in a comparable environment and we are not responsible for any damage or data loss incurred with their use.
You are responsible for reviewing and testing any scripts you run thoroughly before use in any non-testing environment.