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
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import logging
from config.config import config
import json
import logging.handlers
import queue
from rich.logging import RichHandler
from rich import inspect
from rich.theme import Theme
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from rich.markdown import Markdown
from threading import Lock
import re
import os

# Global variable to hold the table's state
log_table = []

custom_theme = Theme(
    {
        'info': 'bright_white',
        'error': 'bold italic red',
        'debug': 'orange1',
        'webex': 'blue',
        'env': 'aquamarine1',
        'success': 'bright_green'
    }
)


def extract_readme_sections():
    readme_path = config.README_PATH
    with open(readme_path, 'r') as file:
        readme_content = file.read()

    patterns = {
        'accessing_app': r'### Accessing the Application\s+(.*?)(?=###|\!\[|$)',
        'running_report': r'### Running the Webex Calling Detailed Report\s+(.*?)(?=###|\!\[|$)',
        'what_to_expect': r'#### What to Expect:\s+(.*?)(?=####|\!\[|$)',
        'please_note': r'#### Please Note:\s+(.*?)(?=####|\!\[|$)'
    }

    extracted_sections = {}
    for section, pattern in patterns.items():
        match = re.search(pattern, readme_content, re.DOTALL)
        if match:
            extracted_sections[section] = match.group(1).strip()

    if extracted_sections:
        combined_sections = '\n\n'.join(extracted_sections.values())
        additional_info_pattern = r'## Additional Info.*'
        combined_sections = re.sub(additional_info_pattern, '', combined_sections, flags=re.DOTALL).strip()
        # Remove any blank lines
        combined_sections = '\n'.join(line for line in combined_sections.split('\n') if line.strip())
        return combined_sections
    return "Relevant sections not found."


class LoggerManager:
    """
    Centralize logging from multiple processes into a single listener that can output to both a file and the terminal without the messages getting jumbled.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.listener = None
        self.console = Console(theme=custom_theme)
        self.log_queue = queue.Queue(-1)  # No limit on size
        self.queue_handler = logging.handlers.QueueHandler(self.log_queue)
        self.logger = self.setup()
        self.original_log_level = self.logger.level
        self.session_logs = {}  # This will store all the logs per session
        self.logger.propagate = False
        self.lock = Lock()

    def ts_print(self, *args, **kwargs):
        """ 1. Thread safe print """
        with self.lock:
            self.console.print(*args, **kwargs)

    def log_and_print(self, message, style="info", level="info"):
        """
        2. Log the message at the given level and print it to the console with the given style.
        """
        # Convert level to lower case to handle different cases (e.g., 'ERROR', 'Error', 'error')
        level = level.lower()

        # Check if the level is a valid logging method and log accordingly
        if level in ["debug", "info", "warning", "error", "critical"]:
            log_method = getattr(self.logger, level)
            log_method(message)  # Log the message
        else:
            self.logger.info(message)  # Default to 'info' level if an invalid level is given

        # Print message to console
        self.ts_print(message, style=style)

    def p_panel(self, *args, **kwargs):
        """
        3. This method creates a Rich Panel with the provided arguments and prints it to the console in a thread-safe manner.
        """
        panel = Panel(*args, **kwargs)
        self.log_and_print(panel)
        # self.ts_print(panel)        # to not log

    def setup(self):
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Ensure the logs directory exists
        log_directory = "logs"
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)

        # Set up file handler for all levels
        file_handler = logging.FileHandler("logs/app.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))

        # Set up console handler for WARNING and above
        console_handler = RichHandler(console=self.console)
        console_handler.setLevel(logging.CRITICAL)

        # Listener that listens to the queue
        self.listener = logging.handlers.QueueListener(
            self.log_queue,
            console_handler,
            file_handler,
            respect_handler_level=True
        )
        self.listener.start()

        # Setup logger
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(self.queue_handler)  # Add QueueHandler

        return logger

    def shutdown(self):
        self.listener.stop()  # Stop the listener when shutting down

    def display_2_column_rich_table(self, data, title):
        """
        Display data in a rich table format.
        """
        table = Table(title=title)
        table.add_column("Variable", justify="left", style="bright_white", width=30)
        table.add_column("Value", style="bright_white", width=60)

        for var_name, var_value in data:
            table.add_row(var_name, str(var_value) if var_value not in [None, ""] else "Not Set")
        self.ts_print(table)

    def display_list_as_rich_table(self, data_list, title, headers=None):
        """
        Display a list of dictionaries in a rich table format with specified headers.
        Args:
            data_list (list): List of dictionaries to display.
            headers (list): List of headers (keys from the dictionaries) to include in the table.
            title (str): Title of the table.
        """
        if not data_list or not isinstance(data_list, list) or not all(isinstance(item, dict) for item in data_list):
            self.ts_print("Invalid data provided for the table.")
            return
        table = Table(title=title)

        if headers is None:  # Determine headers if not provided
            headers = data_list[0].keys() if data_list else []

        for header in headers:  # Add columns to the table based on provided headers or dynamically determined headers
            table.add_column(header, style="bright_white")

        # Populate table rows with data
        for item in data_list:
            row = [str(item.get(header, '')) for header in headers]
            table.add_row(*row)

        self.ts_print(table)

    def display_json_as_rich_table(self, json_data, title="JSON Data"):
        """
        Display JSON data in a rich table format.

        Args:
            json_data (str/dict/list): JSON data to be displayed in the table.
            title (str): Title of the table.
        """
        # Parse JSON if it's a string
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                self.ts_print(f"Invalid JSON string: {e}")
                return

        # Handle case where data is already a dictionary or list
        else:
            data = json_data

        # Create a new table
        table = Table(title=title)

        # Check if the data is a list of dictionaries
        if isinstance(data, list) and all(isinstance(elem, dict) for elem in data):
            # Add headers based on the keys of the first dictionary
            headers = data[0].keys()
            for header in headers:
                table.add_column(header, style="bright_white")

            # Add rows
            for item in data:
                table.add_row(*[str(item.get(h, '')) for h in headers])

        elif isinstance(data, dict):
            # If the data is a single dictionary, display key-value pairs
            table.add_column("Key", style="bright_yellow")
            table.add_column("Value", style="bright_white")
            for key, value in data.items():
                table.add_row(str(key), json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value))

        else:
            self.ts_print("Unsupported JSON format")
            return

        # Print the table
        self.ts_print(table)

    def display_config_table(self, config_instance):
        config_data = [(name, getattr(config_instance, name)) for name in config_instance.model_fields.keys()]
        self.display_2_column_rich_table(config_data, title="Environment Variables")

    def get_config_table(self, config_instance):
        """
        Create a rich table format of the configuration data and return it as a renderable object.

        Args:
            config_instance: The configuration instance containing the settings.

        Returns:
            Table: A rich table object.
        """
        table = Table()
        table.add_column("Variable", justify="left", style="bright_white")
        table.add_column("Value", style="bright_white")

        for name in config_instance.model_fields.keys():
            value = getattr(config_instance, name)
            # Skip rows with empty name and value
            if name or value:
                table.add_row(name, str(value) if value not in [None, ""] else "Not Set")
        return table

    def print_start_panel(self, app_name=config.APP_NAME):
        self.log_and_print(Panel.fit(f'[bold bright_white]{app_name}[/bold bright_white]', title='Start', style='webex'))

    def print_finished_panel(self):
        # Mostly used for non-flask apps
        self.log_and_print(Panel.fit("[bold bright_green]All operations completed successfully. Exiting the application.[/bold bright_green]"))

    def print_exit_panel(self):
        self.log_and_print("\n")
        self.log_and_print(Panel.fit('Shutting down...', title='[bright_red]Exit[/bright_red]', border_style='red'))

    def print_inspect_info(self, obj):
        """
        Inspects and prints detailed information about the given object.

        Args:
            obj: The object to be inspected.
        """
        self.log_and_print(f"Inspecting object: {type(obj).__name__}")
        inspect(obj, methods=True, help=True, private=True, docs=True)

    def debug_inspect(self, obj):
        """
        Inspect an object using Rich and log the representation.
        """
        with self.lock:
            inspect(obj, console=self.console, methods=True)
            self.logger.debug(f"Inspected object: {type(obj).__name__}")

    def handle_exception(self, e):
        """
        Handle an exception by logging it and printing it using Rich.
        """
        with self.lock:
            self.console.print_exception()
            self.logger.exception(f"An exception occurred: {str(e)}")

    def exception(self, message, extra_data=None):
        """Log an exception along with a custom message."""
        if extra_data:
            message += f' - Extra data: {extra_data}'
        self.logger.exception(message)

    def print_start_layout(self):
        layout = Layout()

        # Define the size of header & footer
        header_size = 3
        footer_size = 3

        # Split the layout into three parts: header, body, and footer
        layout.split(
            Layout(name='header', size=header_size),
            Layout(name='body', ratio=1),
            Layout(name='footer', size=footer_size)
        )

        # Split the body into left and right, both with equal ratio
        layout['body'].split_row(
            Layout(name='left', ratio=1),
            Layout(name='right', ratio=1)
        )

        # Header Panel
        app_name = config.APP_NAME
        centered_app_name = Text(app_name, style="bold bright_white")
        header_panel = Panel(centered_app_name,
                             title="Start",
                             title_align="center",
                             style="webex",
                             expand=False,
                             padding=(0, 10)
                             )
        # Left Panel
        config_table = lm.get_config_table(config_instance=config)
        config_table = Align(config_table, align="center", vertical="middle")
        left_panel = Panel(
            config_table,
            title="Environment Variables",
            title_align="center",
            style="env",
            height=24,  # Setting a fixed height for content
            expand=False
        )

        # Right Panel
        usage_content = extract_readme_sections()  # Extract the Usage section from the README
        md = Markdown(usage_content)
        md = Align(md, align="center", vertical="middle")
        right_panel = Panel(
            md,
            title="Usage",
            style="bright_white",
            height=24,  # Setting a fixed height for content
            expand=False
        )

        # Footer Panel
        footer_panel = Panel(
            f"[bright_white]Start URL: {config.PUBLIC_URL}[/bright_white]",
            style="orange1",
            expand=False
        )

        # Use Align to center the panel in the terminal
        centered_panel = Align(header_panel, align="center", vertical="middle")

        # Update layout content
        layout['header'].update(centered_panel)
        layout['left'].update(left_panel)
        layout['right'].update(right_panel)
        layout['footer'].update(footer_panel)

        self.log_and_print(layout)


lm = LoggerManager.get_instance()  # Create a single instance of LoggerManager
