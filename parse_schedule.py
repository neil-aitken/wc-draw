#!/usr/bin/env python3
"""Parse World Cup schedule details and display in calendar order with ET times."""

import re
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Match:
    match_num: int
    date: str
    time_et: str
    team1: str
    team2: str
    venue: str
    stage: str  # Group X, Round of 32, Round of 16, Quarterfinals, Semifinals, Third Place, Final


def parse_utc_offset(offset_str: str) -> int:
    """Parse UTC offset string like 'UTC−6' or 'UTC−4' to hours offset."""
    # Handle both minus sign types (− and -)
    offset_str = offset_str.replace('−', '-').replace('UTC', '').strip()
    return int(offset_str)


def convert_to_et(time_str: str, utc_offset: int) -> str:
    """Convert local time with UTC offset to ET (UTC-5, or UTC-4 during DST).
    
    June/July 2026 is during DST, so ET = UTC-4 (EDT).
    """
    # Parse time like "1:00 p.m." or "12:00 p.m."
    time_str = time_str.strip().lower()
    match = re.match(r'(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?)', time_str)
    if not match:
        return time_str
    
    hour = int(match.group(1))
    minute = int(match.group(2))
    ampm = match.group(3).replace('.', '')
    
    # Convert to 24-hour format
    if ampm == 'pm' and hour != 12:
        hour += 12
    elif ampm == 'am' and hour == 12:
        hour = 0
    
    # Convert local time to UTC, then to ET (EDT = UTC-4 in June/July)
    utc_hour = hour - utc_offset  # Convert to UTC
    et_hour = utc_hour - 4  # Convert UTC to EDT (UTC-4)
    
    # Handle day wraparound
    if et_hour < 0:
        et_hour += 24
    elif et_hour >= 24:
        et_hour -= 24
    
    # Format back to 12-hour time
    if et_hour == 0:
        return f"12:{minute:02d} AM ET"
    elif et_hour < 12:
        return f"{et_hour}:{minute:02d} AM ET"
    elif et_hour == 12:
        return f"12:{minute:02d} PM ET"
    else:
        return f"{et_hour - 12}:{minute:02d} PM ET"


def parse_schedule(content: str) -> list[Match]:
    """Parse the schedule and extract all matches."""
    matches = []
    current_stage = None
    
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect stage headers
        if re.match(r'^Group [A-L]$', line):
            current_stage = line
            i += 1
            continue
        elif line == 'Round of 32':
            current_stage = 'Round of 32'
            i += 1
            continue
        elif line == 'Round of 16':
            current_stage = 'Round of 16'
            i += 1
            continue
        elif line == 'Quarterfinals':
            current_stage = 'Quarterfinals'
            i += 1
            continue
        elif line == 'Semifinals':
            current_stage = 'Semifinals'
            i += 1
            continue
        elif line == 'Match for third place':
            current_stage = 'Third Place'
            i += 1
            continue
        elif line == 'Final':
            current_stage = 'Final'
            i += 1
            continue
        
        # Detect match date line: "June DD, YYYY" or "July DD, YYYY"
        date_match = re.match(r'^((?:June|July) \d{1,2}, \d{4})$', line)
        if date_match and current_stage:
            date_str = date_match.group(1)
            i += 1
            
            # Next line should be time with UTC offset
            if i < len(lines):
                time_line = lines[i].strip()
                time_match = re.match(r'^(\d{1,2}:\d{2}\s*[ap]\.m\.)\s*(UTC[−-]\d+)$', time_line)
                if time_match:
                    local_time = time_match.group(1)
                    utc_offset = parse_utc_offset(time_match.group(2))
                    et_time = convert_to_et(local_time, utc_offset)
                    i += 1
                    
                    # Next line should be teams and match number
                    if i < len(lines):
                        teams_line = lines[i].strip()
                        # Pattern: "Team1 	Match N	 Team2" (with tabs)
                        # For knockout rounds: "Winner Match X<tab>Match N<tab>Winner Match Y"
                        teams_match = re.match(r'^(.+?)\t+Match\s+(\d+)\t+(.+)$', teams_line)
                        if not teams_match:
                            # Try with spaces (group stage format)
                            teams_match = re.match(r'^(.+?)\s+Match\s+(\d+)\s+(.+)$', teams_line)
                        if teams_match:
                            team1 = teams_match.group(1).strip()
                            match_num = int(teams_match.group(2))
                            team2 = teams_match.group(3).strip()
                            i += 1
                            
                            # Skip "Report" line if present (knockout rounds)
                            if i < len(lines) and lines[i].strip() == 'Report':
                                i += 1
                            
                            # Next line should be venue
                            if i < len(lines):
                                venue = lines[i].strip()
                                # Skip if it's another date or header
                                if not re.match(r'^((?:June|July) \d{1,2}, \d{4})$', venue) and venue not in ['Report']:
                                    matches.append(Match(
                                        match_num=match_num,
                                        date=date_str,
                                        time_et=et_time,
                                        team1=team1,
                                        team2=team2,
                                        venue=venue,
                                        stage=current_stage
                                    ))
                                    i += 1
                                    continue
        
        i += 1
    
    return matches


def sort_matches(matches: list[Match]) -> list[Match]:
    """Sort matches by date and time."""
    def sort_key(m: Match):
        # Parse date
        date = datetime.strptime(m.date, "%B %d, %Y")
        
        # Parse ET time
        time_match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', m.time_et)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            ampm = time_match.group(3)
            if ampm == 'PM' and hour != 12:
                hour += 12
            elif ampm == 'AM' and hour == 12:
                hour = 0
            return (date, hour, minute, m.match_num)
        return (date, 0, 0, m.match_num)

    return sorted(matches, key=sort_key)


def display_schedule(matches: list[Match], whatsapp: bool = False):
    """Display the schedule in a nice format."""
    current_date = None

    if whatsapp:
        print("⚽ *2026 FIFA WORLD CUP SCHEDULE* ⚽")
        print("_(All times Eastern)_\n")
    else:
        print("=" * 90)
        print("2026 FIFA WORLD CUP SCHEDULE (All times ET)")
        print("=" * 90)

    for match in matches:
        if match.date != current_date:
            current_date = match.date
            # Parse and format date nicely
            date_obj = datetime.strptime(match.date, "%B %d, %Y")
            day_name = date_obj.strftime("%A")
            if whatsapp:
                print(f"\n📅 *{day_name}, {match.date}*")
            else:
                print(f"\n{'─' * 90}")
                print(f"  {day_name}, {match.date}")
                print(f"{'─' * 90}")

        if whatsapp:
            # Use emoji for stage
            if match.stage.startswith('Group'):
                stage_emoji = "🏟️"
            elif match.stage == 'Round of 32':
                stage_emoji = "🎯"
            elif match.stage == 'Round of 16':
                stage_emoji = "🎯"
            elif match.stage == 'Quarterfinals':
                stage_emoji = "🔥"
            elif match.stage == 'Semifinals':
                stage_emoji = "⭐"
            elif match.stage == 'Third Place':
                stage_emoji = "🥉"
            elif match.stage == 'Final':
                stage_emoji = "🏆"
            else:
                stage_emoji = "⚽"

            # Clean up time display
            time_clean = match.time_et.replace(' ET', '')
            print(f"{stage_emoji} {time_clean} | {match.team1} vs {match.team2}")
            print(f"    📍 {match.venue}")
        else:
            # Format stage column width based on type
            stage_display = match.stage
            if match.stage.startswith('Group'):
                stage_display = match.stage

            print(f"  {match.time_et:<12} Match {match.match_num:3d}  {stage_display:<14}  "
                  f"{match.team1:<25} vs {match.team2}")
            print(f"  {' ' * 12}          {' ' * 14}  {match.venue}")


def main():
    import sys
    whatsapp = '--whatsapp' in sys.argv or '-w' in sys.argv

    with open('group-stage-details', 'r', encoding='utf-8') as f:
        content = f.read()

    matches = parse_schedule(content)
    sorted_matches = sort_matches(matches)

    if not whatsapp:
        print(f"\nTotal matches parsed: {len(sorted_matches)}")

    display_schedule(sorted_matches, whatsapp=whatsapp)

    if not whatsapp:
        # Summary by stage
        print(f"\n{'=' * 90}")
        print("MATCHES BY STAGE")
        print("=" * 90)

        from collections import Counter
        stage_counts = Counter(m.stage for m in sorted_matches)
        stage_order = ['Group A', 'Group B', 'Group C', 'Group D', 'Group E', 'Group F',
                       'Group G', 'Group H', 'Group I', 'Group J', 'Group K', 'Group L',
                       'Round of 32', 'Round of 16', 'Quarterfinals', 'Semifinals',
                       'Third Place', 'Final']
        for stage in stage_order:
            if stage in stage_counts:
                print(f"  {stage}: {stage_counts[stage]} matches")

        # Summary by date
        print(f"\n{'=' * 90}")
        print("MATCHES PER DAY")
        print("=" * 90)

        date_counts = Counter(m.date for m in sorted_matches)
        for date, count in sorted(date_counts.items(), key=lambda x: datetime.strptime(x[0], "%B %d, %Y")):
            print(f"  {date}: {count} matches")


if __name__ == '__main__':
    main()