#!/usr/bin/env python3
"""
Script to create elo_ratings.json from eloratings.net TSV data.
Maps 2-letter codes to full country names for all 48 qualified teams
and 22 playoff candidates.
"""

import json
import subprocess
import sys

# Mapping from eloratings.net 2-letter codes to full team names
# Format: code -> (full_name, confederation, fifa_rank_approx)
TEAM_MAPPING = {
    # QUALIFIED TEAMS (44)
    # Hosts (3)
    "US": ("United States", "CONCACAF", 16),
    "CA": ("Canada", "CONCACAF", 48),
    "MX": ("Mexico", "CONCACAF", 14),
    
    # UEFA (13)
    "ES": ("Spain", "UEFA", 1),
    "EN": ("England", "UEFA", 4),
    "FR": ("France", "UEFA", 3),
    "DE": ("Germany", "UEFA", 10),
    "NL": ("Netherlands", "UEFA", 7),
    "PT": ("Portugal", "UEFA", 6),
    "BE": ("Belgium", "UEFA", 5),
    "HR": ("Croatia", "UEFA", 12),
    "AT": ("Austria", "UEFA", 22),
    "CH": ("Switzerland", "UEFA", 15),
    "NO": ("Norway", "UEFA", 50),
    "RS": ("Serbia", "UEFA", 33),  # RS = Serbia
    "SQ": ("Scotland", "UEFA", 51),  # SQ = Scotland
    
    # CONMEBOL (6)
    "AR": ("Argentina", "CONMEBOL", 2),
    "BR": ("Brazil", "CONMEBOL", 9),
    "CO": ("Colombia", "CONMEBOL", 11),
    "UY": ("Uruguay", "CONMEBOL", 13),
    "EC": ("Ecuador", "CONMEBOL", 31),
    "PY": ("Paraguay", "CONMEBOL", 55),
    
    # CONCACAF (3 more beyond hosts)
    "PA": ("Panama", "CONCACAF", 37),
    "HT": ("Haiti", "CONCACAF", 92),
    "CW": ("Curaçao", "CONCACAF", 82),  # Need to find code
    
    # CAF (9)
    "MA": ("Morocco", "CAF", 18),
    "SN": ("Senegal", "CAF", 21),
    "EG": ("Egypt", "CAF", 36),
    "NG": ("Nigeria", "CAF", 28),  # NG = Nigeria
    "CI": ("Ivory Coast", "CAF", 38),
    "ZA": ("South Africa", "CAF", 60),
    "CM": ("Cameroon", "CAF", 44),
    "DZ": ("Algeria", "CAF", 30),
    "CV": ("Cape Verde", "CAF", 62),
    
    # AFC (7)
    "JP": ("Japan", "AFC", 17),
    "IR": ("Iran", "AFC", 20),
    "KR": ("South Korea", "AFC", 23),
    "SA": ("Saudi Arabia", "AFC", 57),
    "AU": ("Australia", "AFC", 26),
    "QA": ("Qatar", "AFC", 35),
    "UZ": ("Uzbekistan", "AFC", 63),
    
    # OFC (1)
    "NZ": ("New Zealand", "OFC", 99),
    
    # AFC + CONMEBOL remaining
    "JO": ("Jordan", "AFC", 68),
    "GH": ("Ghana", "CAF", 43),  # Actually already in CAF list
    
    # UEFA PLAYOFF TEAMS (16 teams in 4 paths)
    # Path A: Italy, Wales, Bosnia, Northern Ireland
    "IT": ("Italy", "UEFA", 8),
    "WA": ("Wales", "UEFA", 27),
    "BA": ("Bosnia and Herzegovina", "UEFA", 77),
    "NI": ("Northern Ireland", "UEFA", 78),
    
    # Path B: Ukraine, Poland, Albania, Sweden
    "UA": ("Ukraine", "UEFA", 24),
    "PL": ("Poland", "UEFA", 25),
    "AL": ("Albania", "UEFA", 64),
    "SE": ("Sweden", "UEFA", 45),
    
    # Path C: Turkey, Slovakia, Kosovo, Romania  
    "TR": ("Turkey", "UEFA", 32),
    "SK": ("Slovakia", "UEFA", 42),
    "KO": ("Kosovo", "UEFA", 107),
    "RO": ("Romania", "UEFA", 39),
    
    # Path D: Denmark, Czech Republic, Ireland, North Macedonia
    "DK": ("Denmark", "UEFA", 19),
    "CZ": ("Czech Republic", "UEFA", 34),
    "IE": ("Ireland", "UEFA", 53),
    "NM": ("North Macedonia", "UEFA", 72),  # NM code to verify
    
    # IC PATH 1: DR Congo, Jamaica, New Caledonia
    "CD": ("DR Congo", "CAF", 56),
    "JM": ("Jamaica", "CONCACAF", 65),
    "NC": ("New Caledonia", "OFC", 159),  # Code to verify
    
    # IC PATH 2: Iraq, Bolivia, Suriname
    "IQ": ("Iraq", "AFC", 52),
    "BO": ("Bolivia", "CONMEBOL", 80),
    "SR": ("Suriname", "CONCACAF", 135),
}

# Alternative codes and names we might encounter
ALTERNATE_CODES = {
    "SER": "RS",  # Serbia
    "SCO": "SQ",  # Scotland  
    "NIR": "NI",  # Northern Ireland
    "BIH": "BA",  # Bosnia
    "CRC": "CR",  # Costa Rica
    "KSA": "SA",  # Saudi Arabia
    "UAE": "AE",  # UAE
    "MKD": "NM",  # North Macedonia
}


def fetch_elo_data():
    """Fetch current Elo ratings from eloratings.net"""
    result = subprocess.run(
        ["curl", "-s", "https://www.eloratings.net/2024.tsv"],
        capture_output=True,
        text=True
    )
    return result.stdout


def parse_elo_tsv(tsv_data):
    """Parse the TSV data and extract Elo ratings"""
    elo_by_code = {}
    for line in tsv_data.strip().split('\n'):
        fields = line.split('\t')
        if len(fields) >= 4:
            code = fields[2]
            try:
                elo = int(fields[3])
                elo_by_code[code] = elo
            except (ValueError, IndexError):
                continue
    return elo_by_code


def create_elo_json(elo_by_code):
    """Create the final JSON structure"""
    teams = {}
    
    missing = []
    
    for code, (name, confed, fifa_rank) in TEAM_MAPPING.items():
        if code in elo_by_code:
            teams[name] = {
                "elo": elo_by_code[code],
                "confederation": confed,
                "fifa_rank": fifa_rank,
                "code": code
            }
        else:
            missing.append((code, name))
    
    if missing:
        print(f"Warning: Missing Elo data for: {missing}", file=sys.stderr)
        # For missing teams, estimate Elo from FIFA rank
        # Using rough formula: elo ≈ 1800 - (fifa_rank - 20) * 6
        for code, name in missing:
            _, confed, fifa_rank = TEAM_MAPPING[code]
            estimated_elo = max(1000, 1800 - (fifa_rank - 20) * 6)
            teams[name] = {
                "elo": estimated_elo,
                "confederation": confed,
                "fifa_rank": fifa_rank,
                "code": code,
                "estimated": True
            }
            print(f"  Estimated {name}: {estimated_elo}", file=sys.stderr)
    
    return teams


def main():
    print("Fetching Elo data from eloratings.net...", file=sys.stderr)
    tsv_data = fetch_elo_data()
    
    print("Parsing TSV data...", file=sys.stderr)
    elo_by_code = parse_elo_tsv(tsv_data)
    print(f"Found {len(elo_by_code)} teams in Elo data", file=sys.stderr)
    
    # Print all codes for debugging
    print("\nAll codes in Elo data:", file=sys.stderr)
    for code in sorted(elo_by_code.keys()):
        print(f"  {code}: {elo_by_code[code]}", file=sys.stderr)
    
    print("\nCreating team JSON...", file=sys.stderr)
    teams = create_elo_json(elo_by_code)
    
    output = {
        "source": "eloratings.net",
        "fetched": "2024-12",
        "teams": teams
    }
    
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
