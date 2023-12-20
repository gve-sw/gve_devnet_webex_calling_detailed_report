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

import csv
import io
import sys
import time
from datetime import datetime
import wxcadm
from logrr import lm
from funcs import write_to_csv
from config.config import config
from webex_api import MyWebex
from rich.spinner import Spinner
from rich.live import Live


class CDRReportProcessor:
    def __init__(self, webex_access_token):
        try:
            self.webex_access_token = webex_access_token
            self.webex = wxcadm.Webex(webex_access_token)
            self.metrics = {
                'total_duration': 0,
                'total_calls': 0,
                'connected_calls': 0,
                'voicemail_calls': 0,
                'response_times': [],
                'call_outcomes': {},
                'department_calls': {},
                'user_calls': {}
            }
        except wxcadm.exceptions.TokenError:
            # Handle the TokenError specifically
            lm.log_and_print('wxcadm.exceptions.TokenError: The Access Token was not accepted by Webex')
            self.webex = None  # Set webex to None if token is invalid

    def fetch_cdr_data(self, num_days=None):
        if not self.webex:
            return None  # Early exit if webex object is not initialized

        try:
            if num_days:
                # Generate report based on the number of days
                report_id = self.webex.org.reports.cdr_report(days=num_days)
                if not report_id:
                    return None
            else:
                # Retrieve start and end dates from config
                start = config.START_DATE
                end = config.END_DATE

                lm.log_and_print(f'[cadet_blue]Running report with Start Date: {start}, End Date: {end}[/cadet_blue]')

                report_id = self.webex.org.reports.cdr_report(start=start, end=end)

            lm.log_and_print(f'Created CDR report with ID: {report_id}')
            report_status = 'unknown'
            timeout = 60 * 30  # 30 minutes timeout
            start_time = time.time()

            with Live(Spinner('dots', text="Fetching CDR report..."), refresh_per_second=10) as live:

                while report_status != 'done':
                    if time.time() - start_time > timeout:
                        lm.log_and_print('Timeout reached while waiting for the report.')
                        return None
                    time.sleep(30)  # Check every 30 seconds
                    report_status = self.webex.org.reports.report_status(report_id)
                    live.update(Spinner('dots', text=f"Waiting for report to complete, current status: {report_status}"))
                live.update(Spinner('dots', text="Report fetched successfully!"))

            report_lines = self.webex.org.reports.get_report_lines(report_id)
            if not report_lines:
                lm.log_and_print('No CDR data available.')
                return None

            return list(csv.DictReader(io.StringIO('\n'.join(report_lines)))), report_id

        except Exception as e:
            lm.log_and_print(f'An error occurred while fetching CDR data: {e}')
            if hasattr(e, 'response'):
                lm.log_and_print(f'Response: {e.response.status_code} - {e.response.text}', style='bold red')
            return None

    def update_department_calls(self, item):
        """Update department call metrics."""

        department = item.get('Department ID', 'Unknown')
        if department not in self.metrics['department_calls']:
            self.metrics['department_calls'][department] = {'total_calls': 0, 'connected_calls': 0, 'voicemail_calls': 0, 'total_duration': 0}
        dept_metrics = self.metrics['department_calls'][department]
        dept_metrics['total_calls'] += 1
        if item.get('Answered', '').lower() == 'true':
            dept_metrics['connected_calls'] += 1
        elif item.get('Call outcome reason', '').lower() == 'voicemail':
            dept_metrics['voicemail_calls'] += 1
        dept_metrics['total_duration'] += int(item.get('Duration', 0)) if item.get('Duration', '').isdigit() else 0

    def update_user_calls(self, item):
        """Update user call metrics."""
        user = item.get('User', 'Unknown')
        if user not in self.metrics['user_calls']:
            self.metrics['user_calls'][user] = {'total_calls': 0, 'connected_calls': 0, 'voicemail_calls': 0, 'total_duration': 0}
        user_metrics = self.metrics['user_calls'][user]
        user_metrics['total_calls'] += 1
        if item.get('Answered', '').lower() == 'true':
            user_metrics['connected_calls'] += 1
        elif item.get('Call outcome reason', '').lower() == 'voicemail':
            user_metrics['voicemail_calls'] += 1
        user_metrics['total_duration'] += int(item.get('Duration', 0)) if item.get('Duration', '').isdigit() else 0

    def transform_department_calls_to_list(self):
        """Transform department calls data into a list of dictionaries."""
        department_calls_list = [
            {
                'Department': dept,
                'TotalCalls': info['total_calls'],
                'ConnectedCalls': info['connected_calls'],
                'VoicemailCalls': info['voicemail_calls'],
                'TotalDuration': info['total_duration']
            }
            for dept, info in self.metrics['department_calls'].items()
        ]
        return department_calls_list

    def transform_user_calls_to_list(self):
        """Transform user calls data into a list of dictionaries."""
        user_calls_list = [
            {
                'User': user,
                'TotalCalls': info['total_calls'],
                'ConnectedCalls': info['connected_calls'],
                'VoicemailCalls': info['voicemail_calls'],
                'TotalDuration': info['total_duration']
            }
            for user, info in self.metrics['user_calls'].items()
        ]
        return user_calls_list

    def process_call_record(self, item):
        """Process individual call record and update metrics."""
        # Convert string to integer for Duration
        duration = int(item.get('Duration', 0)) if item.get('Duration', '').isdigit() else 0
        self.metrics['total_duration'] += duration
        self.metrics['total_calls'] += 1

        # Determine if the call was connected or went to voicemail
        answered = item.get('Answered', '').lower() == 'true'
        call_outcome_reason = item.get('Call outcome reason', '').lower()
        if answered:
            self.metrics['connected_calls'] += 1
        elif call_outcome_reason == 'voicemail':
            self.metrics['voicemail_calls'] += 1

        # Parse datetime strings if present
        answer_time_str = item.get('Answer time', '')
        start_time_str = item.get('Start time', '')
        if answer_time_str and start_time_str:
            try:
                answer_time = datetime.fromisoformat(answer_time_str)
                start_time = datetime.fromisoformat(start_time_str)
                response_time = (answer_time - start_time).total_seconds()
                self.metrics['response_times'].append(response_time)
            except ValueError:
                pass  # Ignore if datetime parsing fails

        outcome = item.get('Call outcome', 'Unknown')
        self.metrics['call_outcomes'][outcome] = self.metrics['call_outcomes'].get(outcome, 0) + 1

        # Update department and user calls
        self.update_department_calls(item)
        self.update_user_calls(item)

    def process_all_cdr_records(self, cdr_data):
        """Process all items in the fetched CDR data."""
        try:
            for item in cdr_data:
                self.process_call_record(item)
        except TypeError as e:
            lm.log_and_print(f'Error processing CDR data: {e}')

    def get_all_reports(self):
        try:
            return self.webex.org.reports.list_reports()
        except Exception as e:
            lm.log_and_print(f'Error listing reports: {e}')
            return None

    def handle_existing_reports(self):
        existing_reports = self.get_all_reports()
        num_existing_reports = len(existing_reports)

        lm.display_list_as_rich_table(data_list=existing_reports, title='Current Report List',
                                      headers=['title', 'startDate', 'endDate', 'downloadURL', 'Id'])

        if num_existing_reports == 50:
            lm.log_and_print('[bright_red]You have reached the maximum number of reports ([/bright_red]' + '[bright_white]50[/bright_white]' +
                             '[bright_red]).[/bright_red]' +
                             '\n[orange1]Current number of reports: [/orange1]' + f'[bright_white]{num_existing_reports}[/bright_white]'
                             '\n[bright_green]Please delete at least one report to proceed...[/bright_green]')

            # Display options in a list format
            lm.log_and_print('Options:\n1: Delete report by ID\n2: Delete all reports\n3: Exit', style='bright_white')
            delete_option = input('Enter your choice (1, 2, or 3): ').strip()

            webex_api = MyWebex(self.webex_access_token)

            if delete_option == '1':
                report_id_to_delete = input('Enter the report ID to delete: ').strip()
                webex_api.delete_report(report_id_to_delete)
            elif delete_option == '2':
                for report in existing_reports:
                    webex_api.delete_report(report['Id'])
            elif delete_option == '3':
                sys.exit(1)

            existing_reports = self.get_all_reports()  # Re-fetch the reports to update the count
            num_existing_reports = len(existing_reports)  # Update the count

        # Return True if processing can continue, False if not
        return num_existing_reports < 50

    def fetch_cdr_data_based_on_config(self):
        if isinstance(config.NUMBER_OF_DAYS_CDR_REPORT, int) and config.NUMBER_OF_DAYS_CDR_REPORT:
            return self.fetch_cdr_data(num_days=config.NUMBER_OF_DAYS_CDR_REPORT)
        elif config.START_DATE and config.END_DATE:
            return self.fetch_cdr_data()
        else:
            lm.log_and_print('No valid date range or number of days provided for CDR report.', style='bold red')
            return None

    def run_report(self):
        try:
            if not self.handle_existing_reports():
                return

            cdr_data, report_id = self.fetch_cdr_data_based_on_config()  # Run report

            if cdr_data:
                write_to_csv(cdr_data)  # Output raw report to csv file
                self.process_all_cdr_records(cdr_data)  # Process the fetched CDR data
                department_calls_list = self.transform_department_calls_to_list()
                user_calls_list = self.transform_user_calls_to_list()
                # lm.display_list_as_rich_table(data_list=department_calls_list, title='Department Calls Summary')  # Output to console
                # lm.display_list_as_rich_table(data_list=user_calls_list, title='User Calls Summary')  # Output to console

                # Delete the report after processing
                webex_api = MyWebex(self.webex_access_token)
                webex_api.delete_report(report_id)

                lm.print_finished_panel()
            else:
                lm.log_and_print('No CDR data available to process.', style='bold red')
        except Exception as e:
            lm.log_and_print(f'An error occurred while running the report: {str(e)}', style='bold red')
