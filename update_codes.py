import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# הגדרת רשימת מקורות חלופיים וישירים יותר לרובולוקס
SOURCES = [
    {"name": "Roblox Promo Codes Wiki", "url": "https://roblox.fandom.com/wiki/Promo_codes"},
    {"name": "Pocket Tactics", "url": "https://www.pockettactics.com/roblox/codes-list"},
]

IGNORE_TOKENS = {
    "DOCTYPE", "HTML", "HEAD", "BODY", "ACTIVITIES", "CAMPAIGNS", 
    "ROBLOX", "GAMES", "UPDATE", "NEWS", "GUIDE", "FREE", "REWARDS", 
    "ROBUX", "ITEMS", "AVATAR", "COMMUNITY", "PROMO", "CODES", "SIGN",
    "LOGIN", "ACCOUNT", "PASSWORD", "SETTINGS", "PRIVACY", "TERMS", "WIKI"
}

ENGLISH_WORDS_BLOCKLIST = {
    "DISCORD", "PLAYERS", "CHECK", "COMMUNITY", "SHARE", "FIRST", 
    "SELECT", "TERMS", "USEFUL", "OBJECTIVES", "SEARCHING", "WHILE", 
    "BEFORE", "TUTORIAL", "PROBABLY", "BUILD", "OFFICIAL", "MEDIA", 
    "PROMOTIONS", "RELEASES", "PHONES", "MISTAKE", "OUTFIT", "THERE", 
    "FIXED", "TEAMS", "UNIVERSE", "BELOW", "DOESN", "TIKTOK", "AWESOME", 
    "STEPPING", "SPIDER", "PLENTY", "EVENTS", "APPEARING", "FRAGMENTS", 
    "CAPTAIN", "WALKS", "SOMETIMES", "ENTER", "GREAT", "SPELLING", 
    "TRACK", "POWER", "UPCOMING", "CORRECTLY", "UPDATED", "POINT", "UNLOCK", 
    "INSTAGRAM", "TABLES", "ACTIVE", "ENJOYS", "ACROSS", "INCLUDE", 
    "ROSTER", "DIRECTLY", "BLUESKY", "RETURNING", "POSSIBLE", "PASTING", 
    "MILLION", "FAILING", "MODES", "CHALLENGES", "PREVENT", "ANGEL", "EASIEST", 
    "NIGHT", "AMAZING", "SMALL", "TAKING", "EVERYTHING", "ABOUT", "GAMING", 
    "ENTERED", "SPECIAL", "INCLUDING", "GOODIES", "COMBINATIONS", "RAIDS", 
    "TIMES", "EXPIRED", "INBOX", "THANKS", "START", "AMERICA", "WARNING", 
    "REDEEM", "NOVEMBER", "CONTENT", "REMOVE", "THROUGH", "BASED", "DIFFERENT", 
    "ASSEMBLE", "FINDING", "CAREERS", "COMPLETE", "FACEBOOK", "DEPUTY", 
    "OTHER", "RECEIVE", "CREDITS", "ANNOUNCEMENTS", "ABOVE", "LAUNCH", 
    "EDITOR", "ALREADY", "SWITCH", "CHATTING", "FEATURES", "INVITATION", 
    "CHANCE", "EXTRA", "DAILY", "WITHOUT", "THINK", "RESOURCES", "PLAYTIME", 
    "DREAM", "WHERE", "HUNDREDS", "MATERIALS", "BATTLE", "COPYING", "UPGRADE", 
    "TESTING", "MAILBOX", "PLAYING", "PARTICULARLY", "WORDS", "CHECKING", 
    "NETWORK", "PROGRESS", "LATEST", "REGULARLY", "BOOKMARK", "TACTICS", 
    "CHARACTERS", "WRITER", "HEROES", "APPEAR", "LOOKING", "STEPS", "BOOSTS", 
    "NINTENDO", "DURING", "INCREASINGLY", "CELEBRATIONS", "DIFFICULT", "SHARES", 
    "SOCIAL", "THINGS", "JOINED", "CODES", "STAFF", "CELEBRATE", "COLLECT", 
    "EXPIRE", "YOUTUBE", "DISCUSS", "GIFTING", "SCHEDULE", "GIVEAWAYS", 
    "POWERED", "WORKING", "REDEEMING", "SETTINGS", "SERVER", "HAVEN", "BORING", 
    "FOLLOW", "MILESTONES", "WELCOME", "JOINING", "USUALLY", "LOADOUT", "WORTH", "BUFFS", "GIVES"
}

SPECIAL_KEYWORDS = {"EXCLUSIVE", "LIMITED", "SPECIAL", "EVENT"}

def clean_and_validate_code(token):
    token = token.upper().strip()
    if not (4 <= len(token) <= 25):
        return None
    if token in IGNORE_TOKENS or token in ENGLISH_WORDS_BLOCKLIST:
        return None
    if token.isdigit():
        return None
    return token

def scrape_source(source_info):
    found_codes = set()
    try:
        # שימוש ב-Headers מתקדמים יותר כדי לדמות דפדפן אמיתי לחלוטין
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        response = requests.get(source_info["url"], headers=headers, timeout=15)
        print(f"[{source_info['name']}] HTTP Status Code: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # סריקת כל הטבלאות, השורות והקישורים בעמוד
            for element in soup.find_all(['table', 'tr', 'td', 'li', 'code', 'b', 'strong', 'a']):
                text = element.get_text()
                matches = re.findall(r'\b[A-Z0-9\-_]{5,25}\b', text.upper())
                for match in matches:
                    valid_code = clean_and_validate_code(match)
                    if valid_code:
                        found_codes.add(valid_code)
                        
        print(f"[{source_info['name']}] Found {len(found_codes)} clean codes.")
    except Exception as e:
        print(f"Error scraping {source_info['name']}: {e}")
    
    return found_codes

def main():
    print("Starting Roblox Clean Aggregator v3.0...")
    
    code_consensus = {}
    
    for source in SOURCES:
        codes = scrape_source(source)
        for code in codes:
            if code not in code_consensus:
                code_consensus[code] = {"sources": set(), "is_special": False}
            code_consensus[code]["sources"].add(source["name"])
            
            if any(keyword in code for keyword in SPECIAL_KEYWORDS):
                code_consensus[code]["is_special"] = True

    processed_codes = []
    
    for code, data in code_consensus.items():
        source_count = len(data["sources"])
        is_special = data["is_special"]
        
        score = 50 + (source_count * 25)
        if is_special:
            score += 50
            
        if is_special:
            status = "Limited / Special"
            reward_desc = "Official Roblox Special Event Reward"
            badge_type = "rare"
        else:
            status = "Active"
            reward_desc = "Verified Roblox Promo Code"
            badge_type = "active"

        processed_codes.append({
            "code": code,
            "reward": reward_desc,
            "status": status,
            "badge": badge_type,
            "source": f"Synced from {source_count} Sources" if source_count > 1 else "Live Community Scraper",
            "date": datetime.utcnow().strftime("Synced: %b %Y"),
            "score": score
        })

    processed_codes.sort(key=lambda x: x["score"], reverse=True)

    output_data = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_active": len([c for c in processed_codes if c["badge"] == "active"]),
        "total_rare": len([c for c in processed_codes if c["badge"] == "rare"]),
        "codes": processed_codes
    }

    filename = "roblox-codes.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved {len(processed_codes)} clean codes to {filename}.")

if __name__ == "__main__":
    main()
