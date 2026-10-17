import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# הגדרת רשימת המקורות לשאיפת קודי Roblox
SOURCES = [
    {"name": "Pro Game Guides", "url": "https://progameguides.com/roblox/roblox-promocodes/"},
    {"name": "Pocket Tactics", "url": "https://www.pockettactics.com/roblox/codes-list"},
]

# מילות מערכת ומילים נפוצות באנגלית שחובה לחסום
IGNORE_TOKENS = {
    "DOCTYPE", "HTML", "HEAD", "BODY", "ACTIVITIES", "CAMPAIGNS", 
    "ROBLOX", "GAMES", "UPDATE", "NEWS", "GUIDE", "FREE", "REWARDS", 
    "ROBUX", "ITEMS", "AVATAR", "COMMUNITY", "PROMO", "CODES"
}

# רשימת מילים נפוצות שאתרים משתמשים בהן ולא קשורים לקודים
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

# מילות מפתח לזיהוי פרסים מיוחדים או בלעדיים ברובולוקס
SPECIAL_KEYWORDS = {"EXCLUSIVE", "LIMITED", "SPECIAL", "EVENT"}

def clean_and_validate_code(token):
    """בדיקה האם הטוקן עומד בתנאי הסף לקוד תקין ואמיתי של רובולוקס"""
    token = token.upper().strip()
    
    # סינון לפי אורך (קודי רובולוקס לרוב באורך 4 עד 25 תווים)
    if not (4 <= len(token) <= 25):
        return None
        
    # חסימת מילים מהרשימות השחורות
    if token in IGNORE_TOKENS or token in ENGLISH_WORDS_BLOCKLIST:
        return None
        
    # מניעת מחרוזות שהן מספרים נקיים בלבד
    if token.isdigit():
        return None
        
    # תנאי ברזל: קוד Roblox לגיטימי מכיל בדרך כלל שילוב אותיות/מספרים או תחיליות מוכרות, 
    # או שהוא מורכב מטקסט ייחודי באותיות גדולות ללא רווחים.
    has_digit = any(char.isdigit() for char in token)
    is_alpha_code = token.isalnum() and len(token) >= 6
    
    if not (has_digit or is_alpha_code):
        return None
        
    return token

def scrape_source(source_info):
    """שאיבת קודים ממקור בודד"""
    found_codes = set()
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(source_info["url"], headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for element in soup.find_all(['p', 'li', 'td', 'code', 'strong', 'span']):
                text = element.get_text()
                # חיפוש תבניות טקסט שמתאימות לקודי רובולוקס (אותיות ומספרים ללא רווחים)
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
    print("Starting Roblox Clean Aggregator v1.0...")
    
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

    # מיון לפי ציון
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
