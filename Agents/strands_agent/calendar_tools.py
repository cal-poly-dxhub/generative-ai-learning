from datetime import datetime, timedelta

from strands import tool

from auth import get_calendar_service


@tool
def get_calendar_events(days_ahead: int = 7) -> str:
    """Get Google Calendar events for the upcoming days to check availability.

    Returns a list of calendar events with their times so you can determine
    when the user is free to schedule meetings.

    Args:
        days_ahead: Number of days ahead to check (default 7)
    """
    service = get_calendar_service()

    now = datetime.utcnow()
    time_min = now.isoformat() + "Z"
    time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])
    if not events:
        return f"No calendar events found in the next {days_ahead} days. The user appears to be fully available."

    events_by_date = {}

    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))
        summary = event.get("summary", "(No title)")
        status = event.get("status", "confirmed")

        if "T" in start:
            date_key = start.split("T")[0]
            start_time = start.split("T")[1][:5]
            end_time = end.split("T")[1][:5] if "T" in end else "all day"
            time_str = f"{start_time} - {end_time}"
        else:
            date_key = start
            time_str = "All day"

        if date_key not in events_by_date:
            events_by_date[date_key] = []

        events_by_date[date_key].append(f"  {time_str}: {summary} (status: {status})")

    output_lines = [f"Calendar events for the next {days_ahead} days:\n"]
    for date in sorted(events_by_date.keys()):
        output_lines.append(f"{date}:")
        output_lines.extend(events_by_date[date])
        output_lines.append("")

    return "\n".join(output_lines)
