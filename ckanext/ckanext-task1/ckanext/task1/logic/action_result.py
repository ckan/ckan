# action_result.py
from typing import Dict

class ActionResult:
    class TrackingUrlsPerDay(Dict):
        date: str
        url: str
        count: int

    class TrackingUrlsPerMonth(Dict):
        month: str
        url: str
        count: int