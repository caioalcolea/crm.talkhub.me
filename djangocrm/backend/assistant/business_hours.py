"""
Business hours enforcement for the assistant scheduler.

Checks if a datetime falls within an organization's configured business hours
and calculates the next available business hour for deferred jobs.
"""

import logging
from datetime import datetime, time, timedelta

from django.utils import timezone

import pytz

logger = logging.getLogger(__name__)


def is_within_business_hours(org, dt=None):
    """
    Check if a datetime is within the org's business hours.

    Args:
        org: Organization instance
        dt: Datetime to check (default: now)

    Returns:
        bool: True if within business hours or if no business hours configured
    """
    config = getattr(org, "business_hours", None) or {}
    windows = config.get("windows")
    if not windows:
        return True  # No restriction

    tz_name = config.get("timezone", "America/Sao_Paulo")
    try:
        tz = pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning("Unknown timezone %s for org %s, allowing", tz_name, org.id)
        return True

    if dt is None:
        dt = timezone.now()

    local_dt = dt.astimezone(tz)
    current_day = local_dt.isoweekday()  # 1=Monday, 7=Sunday
    current_time = local_dt.time()

    for window in windows:
        days = window.get("days", [])
        start_str = window.get("start", "00:00")
        end_str = window.get("end", "23:59")

        if current_day not in days:
            continue

        try:
            start = time.fromisoformat(start_str)
            end = time.fromisoformat(end_str)
        except (ValueError, TypeError):
            continue

        if start <= current_time <= end:
            return True

    return False


def next_business_hour(org, dt=None):
    """
    Find the next datetime that falls within business hours.

    Args:
        org: Organization instance
        dt: Starting datetime (default: now)

    Returns:
        datetime: Next available business hour, or dt if no config
    """
    config = getattr(org, "business_hours", None) or {}
    windows = config.get("windows")
    if not windows:
        return dt or timezone.now()

    tz_name = config.get("timezone", "America/Sao_Paulo")
    try:
        tz = pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:
        return dt or timezone.now()

    if dt is None:
        dt = timezone.now()

    local_dt = dt.astimezone(tz)

    # Search up to 8 days ahead (covers a full week + buffer)
    for day_offset in range(8):
        check_date = local_dt.date() + timedelta(days=day_offset)
        check_day = check_date.isoweekday()

        for window in windows:
            days = window.get("days", [])
            start_str = window.get("start", "08:00")

            if check_day not in days:
                continue

            try:
                start = time.fromisoformat(start_str)
            except (ValueError, TypeError):
                continue

            candidate = tz.localize(datetime.combine(check_date, start))

            # Must be in the future
            if candidate > dt:
                return candidate

            # If same day and we're before the window end, use current time
            if day_offset == 0:
                end_str = window.get("end", "18:00")
                try:
                    end = time.fromisoformat(end_str)
                except (ValueError, TypeError):
                    continue
                if local_dt.time() <= end:
                    return dt  # Already within or before window end

    # Fallback: return next day at 8 AM in org timezone
    fallback = tz.localize(
        datetime.combine(local_dt.date() + timedelta(days=1), time(8, 0))
    )
    return fallback
