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
        if not self.kitty_msg_center:
            self.nvim.out_write("PythonAppRunner: no kitty remote control set up")

        self.config = self.get_config()
        self.python = self.get_python_executable(self.config)

    @pynvim.command('RunPythonApp', sync=True)
    def run_python_app(self):

        # Only act if prerequisits are present
        if self.config and self.python and self.kitty_msg_center:

            if not self.kitty_app_runner_window_exists():
                self.make_kitty_apprunner_window()

            app = self.config['entrypoint']
            args = self.config['arguments']

            self.run(f"{self.python} {app} {args}")

    def get_config(self) -> Optional[dict]:
        """
        Look in buffer directory and in all parent directories for config file.
        """
        cwd = Path(self.nvim.eval('getcwd()'))

        # Look for config file in current directory
        config_file = cwd / self.config_file_name
        if not config_file.exists():
            # Look for config file in git root directory all parents
            found_git = False
            for parent_dir in cwd.parents:
                if (parent_dir / '.git').is_dir():
                    found_git = True
                    config_file = parent_dir / self.config_file_name
                    if config_file.exists():
                        break
        if not found_git:
            self.nvim.out_write('PythonAppRunner: .git directory not found in parent directories')

        if not config_file.exists():
            self.nvim.out_write(f'PythonAppRunner: {self.config_file_name} not found in .git root')
        else:
            with open(config_file, "r") as config_handle:
                return json.load(config_handle)

    def get_python_executable(self, config) -> Optional[str]:

        if config['python_executable']:
            python = config['python_executable']
        else:
            python = self.nvim.vars.get('python3_host_prog')

        if not python:
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

        self.nvim.out_write("PythonAppRunner: about to make window")
        if subprocess.run(cmd, shell=True).returncode == 1:
            self.nvim.out_write(f'PythonAppRunner: kitty window could not be made')
