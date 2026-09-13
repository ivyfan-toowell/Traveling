"""Reliable local date tools used by planning agents."""

from datetime import datetime
from zoneinfo import ZoneInfo

from langchain.tools import tool


def _today_in_china() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")


@tool("get-current-date", description="获取中国标准时间下的当前日期（YYYY-MM-DD）。")
def get_current_date() -> str:
    return _today_in_china()


@tool("getTodayDate", description="获取中国标准时间下的当前日期（YYYY-MM-DD）。")
def get_today_date() -> str:
    return _today_in_china()
