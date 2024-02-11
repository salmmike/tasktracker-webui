"""
Web UI for adding tasks.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
USA

Author: Mike Salmela
"""
from enum import Enum, IntEnum
import datetime
import time
import pathlib
import configparser
import logging


import requests

from flask import Flask, render_template, request

from waitress import serve

CONFIG_FILE_PATH = pathlib.Path("/etc/tasktracker/tasktracker.ini")
INPUT_TASK_HTML = "input_task.html"
logger = logging.getLogger("tasktracker_web_ui")


class RepeatInfo(IntEnum):
    """
    Different task repeat types.
    """

    NO_REPEAT = 0
    MONTHLY = 1
    MONTHLY_DAY = 2
    SPECIFIED_DAYS = 3
    WITH_INTERVAL = 4


def get_config() -> configparser.ConfigParser:
    """
    Get the tasktracker configuration
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)
    return config


class _AddTaskFields(str, Enum):
    START = "task_start"
    TIME = "task_time"
    NAME = "task_name"
    REPEAT_INFO = "repeat_info"


def _get_repeat_info(info):
    """
    Repeat info enum to values.
    """
    if info == "daily":
        return RepeatInfo.SPECIFIED_DAYS, 1234567
    if info == "weekly":
        return RepeatInfo.WITH_INTERVAL, 7
    if info == "weekdays":
        return RepeatInfo.SPECIFIED_DAYS, 12345
    if info == "biweekly":
        return RepeatInfo.WITH_INTERVAL, 14
    if info == "once":
        return RepeatInfo.NO_REPEAT, 0
    if info == "monthly":
        return RepeatInfo.MONTHLY, 0
    if info == "four_weeks":
        return RepeatInfo.WITH_INTERVAL, 7*4
    raise RuntimeError("Wrong repeat info!")


class WebUIError(RuntimeError):
    """
    Error for WebUI
    """


class TaskTrackerWebUI:
    """
    Provides a webui for adding tasks to the TaskTracker application.
    """

    def __init__(self, config: configparser.ConfigParser) -> None:
        self._config = config

    def start(self):
        """
        Start the webui
        """
        app = self._make_app()
        host = "0.0.0.0"
        print(f"Running on {host}:{self._port}")
        serve(app, host=host, port=self._port)

    @property
    def _port(self):
        return self._config["webui"]["port"]

    @property
    def _api_address(self):
        return self._config["tasktrackerapi"]["hostaddress"]

    @property
    def _api_port(self):
        return self._config["tasktrackerapi"]["port"]

    @property
    def _add_task(self):
        return self._config["tasktrackerapi"]["addTaskApi"]

    @property
    def _task_post_addr(self):
        return f"{self._api_address}:{self._api_port}/{self._add_task}"

    def post_add_task(self, data: dict):
        """
        Add task to tasktracker
        """
        try:
            start_date = [int(x) for x in data.get(_AddTaskFields.START).split("-")]
            if len(start_date) != 3:
                err = (
                    f"{_AddTaskFields.START.value} len incorrect."
                    f" Was {len(start_date)}. {start_date}"
                )

                raise ValueError(err)
        except ValueError as exc:
            logger.error("Error in post data: %s", exc)
            raise WebUIError("Invalid value for start date!") from exc
        try:
            start_time = [int(x) for x in data.get(_AddTaskFields.TIME).split(":")]
            if len(start_time) != 2:
                err = (
                    f"{_AddTaskFields.TIME.value} len incorrect. "
                    f"Was {len(start_time)}. {start_time}"
                )
                raise ValueError(err)
        except (ValueError, AttributeError) as exc:
            logger.error("Error in post data: %s", exc)
            raise WebUIError("Invalid value for start time!") from exc

        if not data.get(_AddTaskFields.NAME):
            logger.error("Error in post data: No data in %s", _AddTaskFields.NAME.value)
            raise WebUIError("No task name!")

        time_t = datetime.datetime(
            year=start_date[0],
            month=start_date[1],
            day=start_date[2],
            hour=start_time[0],
            minute=start_time[1],
        )

        time_t = int(time.mktime(time_t.timetuple()))
        repeat_type, repeat_info = _get_repeat_info(
            data.get(_AddTaskFields.REPEAT_INFO)
        )

        jsondata = {
            "taskName": data.get(_AddTaskFields.NAME),
            "taskStart": time_t,
            "taskRepeatInfo": repeat_info,
            "taskRepeatType": repeat_type,
        }

        resp = requests.post(
            url=self._task_post_addr, json=jsondata, verify=False, timeout=10
        )
        if resp.status_code != 200:
            raise RuntimeError(resp.text)

    def _make_app(self) -> Flask:
        app = Flask(__name__)

        @app.route("/", methods=["POST", "GET"])
        def create_task():
            try:
                if request.method == "GET":
                    return render_template(INPUT_TASK_HTML)
                if request.method == "POST":
                    print(request.form.to_dict())
                    self.post_add_task(request.form.to_dict())
                    return render_template(INPUT_TASK_HTML)
            except WebUIError as err:
                return str(err)
            except requests.exceptions.ConnectionError as err:
                logger.error("ConnectionError: %s", err)
                return "Failed to connect to TaskTracker API."
            return 404

        return app


def start():
    """
    Start the TaskTracker webui
    """
    config = get_config()
    webui = TaskTrackerWebUI(config)
    webui.start()


if __name__ == "__main__":
    start()
