"""
TODO needs tidying up, better separation of logic when using config file and when launching current
active script.
"""
import pynvim
import json
import subprocess
import os
from pathlib import Path
from typing import Optional


@pynvim.plugin
class PythonAppRunner(object):

    def __init__(self, nvim):
        self.nvim = nvim
        self.config_file_name = 'python_runner_config.json'
        self.apprunner_window_title = 'python_app_runner'

        self.kitty_msg_center = os.environ.get("KITTY_LISTEN_ON")

        self.config_file_path = self.get_config_file()
        self.python = self.get_python_executable(self.config_file_path)

    @pynvim.command('CloseRunPythonAppWindow', sync=True)
    def close_window(self):

        if not self.kitty_msg_center:
            self.nvim.out_write("PythonAppRunner: no kitty remote control set up")
            return

        # If window doesn't exist, do nothing
        if not self.kitty_app_runner_window_exists():
            return

        self.close_kitty_apprunner_window()

    @pynvim.command('RunPythonApp', sync=True)
    def run_python_app(self):

        if not self.kitty_msg_center:
            self.nvim.out_write("PythonAppRunner: no kitty remote control set up")
            return

        if not self.kitty_app_runner_window_exists():
            self.make_kitty_apprunner_window()

        # 1) Run script from config
        if self.config_file_path:

            # Read config file every time command is run in case its content has changed
            with open(self.config_file_path, "r") as config_handle:
                config = json.load(config_handle)

                app = Path(config['entrypoint'])
                args = config['arguments']

                self.run(f"cd {app.parent}")
                self.run(f"{self.python} {app} {args}")

        # 2) Run current script
        else:
            # but first cd to current directory
            cwd = Path(self.nvim.eval('getcwd()'))
            current_file = Path(self.nvim.eval('expand("%:p")'))
            self.run(f"cd {cwd}")
            self.run(f"{self.python} {current_file}")

    def get_config_file(self) -> Optional[Path]:
        """
        Look in buffer directory and in all parent directories for config file.
        """
        cwd = Path(self.nvim.eval('getcwd()'))

        # First assume config file can be found in current directory
        config_file = cwd / self.config_file_name

        # if not found there, look in first root directory with .git folder
        if not config_file.exists():
            # Look for config file in git root directory all parents
            found_git = False
            for parent_dir in cwd.parents:
                if (parent_dir / '.git').is_dir():
                    found_git = True
                    config_file = parent_dir / self.config_file_name
                    if config_file.exists():
                        break

                # Only seach in the first directory with .git
                if found_git:
                    break

            if not found_git:
                self.nvim.out_write('PythonAppRunner: .git directory not found in parent directories')

        if config_file.exists():
            return config_file
        else:
            self.nvim.out_write(f'PythonAppRunner: {self.config_file_name} not found in .git root')
            return None

    def get_python_executable(self, config_file: Optional[Path]) -> Optional[str]:

        python = None
        if config_file:
            with open(config_file, "r") as config_handle:
                config = json.load(config_handle)
                python = config['python_executable']

        if not python:
            try:
                python = self.nvim.vars.get('python3_host_prog')
            except ValueError:
                msg = ('PythonAppRunner: python executable not found in'
                       ' configuration or nvim init')
                self.nvim.out_write(msg)

        return python

    def run(self, run_cmd):

        cmd = (f'kitty @ --to {self.kitty_msg_center} send-text'
               f' --match title:{self.apprunner_window_title} {run_cmd}\x0d')

        if subprocess.run(cmd, shell=True).returncode == 1:
            self.nvim.out_write('PythonAppRunner: run command could not be sent')

    def kitty_app_runner_window_exists(self) -> bool:

        target = f'title\": \"{self.apprunner_window_title}\"'
        query = f'kitty @ --to {self.kitty_msg_center} ls'

        kitty_ls_output = subprocess.run(query, shell=True, capture_output=True).stdout
        if target in str(kitty_ls_output):
            return True
        else:
            return False

    def make_kitty_apprunner_window(self):
        cmd = (f'kitty @ --to {self.kitty_msg_center} new-window --keep-focus'
               f' --title {self.apprunner_window_title}')

        if subprocess.run(cmd, shell=True).returncode == 1:
            self.nvim.out_write('PythonAppRunner: kitty window could not be made')

    def close_kitty_apprunner_window(self):
        cmd = (f'kitty @ --to {self.kitty_msg_center} close-window'
               f' --match title:{self.apprunner_window_title}')

        if subprocess.run(cmd, shell=True).returncode == 1:
            self.nvim.out_write('PythonAppRunner: kitty window could not be closed')
