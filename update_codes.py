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

# מילות מערכת ומילים נפוצות באנגלית שחובה לחסום כדי להימנע מזיהוי שגוי
IGNORE_TOKENS = {
    "DOCTYPE", "HTML", "HEAD", "BODY", "ACTIVITIES", "CAMPAIGNS", 
    "ROBLOX", "GAMES", "UPDATE", "NEWS", "GUIDE", "FREE", "REWARDS", 
    "ROBUX", "ITEMS", "AVATAR", "COMMUNITY", "PROMO", "CODES", "SIGN",
    "LOGIN", "ACCOUNT", "PASSWORD", "SETTINGS", "PRIVACY", "TERMS", "WIKI",
    "TABLE", "CLASS", "SPAN", "DIV", "HREF", "HTTP", "HTTPS", "COM"
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

def clean_and_validate_code(token):
    """סינון וניקוי טוקנים שנשלפו מהרשת בהתאם לתבנית קוד לגיטימית"""
    token = token.upper().strip()
    
    # אורך מקובל לקודי רובולוקס
    if not (4 <= len(token) <= 25):
        return None
        
    # מניעת נפילה למילים מתוך רשימות החסימה
    if token in IGNORE_TOKENS or token in ENGLISH_WORDS_BLOCKLIST:
        return None
        
    # מניעת מחרוזות שהן מספרים נקיים בלבד
    if token.isdigit():
        return None
        
    return token

def fetch_source_codes(source):
    """ביצוע בקשת HTTP אמיתית וניתוח תוכן הדף באמצעות BeautifulSoup"""
    url = source["url"]
    found_codes = set()
    
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            timeout=20
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # סריקה ממוקדת של טבלאות, שורות טקסט ואלמנטים שבהם נהוג לפרסם קודים
        for element in soup.find_all(['tr', 'td', 'th', 'li', 'code', 'strong', 'b', 'p']):
            text = element.get_text()
            matches = re.findall(r'\b[A-Z0-9\-_]{5,25}\b', text.upper())
            for match in matches:
                valid_code = clean_and_validate_code(match)
                if valid_code:
                    found_codes.add(valid_code)
                    
        print(f"[{source['name']}] Successfully fetched and extracted {len(found_codes)} candidates.")
        return {
            "source": url,
            "source_name": source["name"],
            "observed_at": datetime.now().astimezone().isoformat(),
            "candidates": list(found_codes),
            "success": True
        }
    except requests.RequestException as exc:
        print(f"Source fetch failed: {url}: {exc}")
        return {
            "source": url,
            "source_name": source["name"],
            "observed_at": datetime.now().astimezone().isoformat(),
            "candidates": [],
            "success": False,
            "error": str(exc)
        }

def main():
    print("Starting Roblox Real-Scraping Aggregator...")
    
    code_consensus = {}
    
    # שלב 1: איסוף מקורות בפועל מהרשת
    source_results = [fetch_source_codes(source) for source in SOURCES]
    
    for result in source_results:
        if result["success"]:
            source_name = result["source_name"]
            observed_time = result["observed_at"]
            for code in result["candidates"]:
                if code not in code_consensus:
                    code_consensus[code] = {
                        "sources": set(), 
                        "last_observed": observed_time
                    }
                code_consensus[code]["sources"].add(source_name)

    processed_codes = []
    
    # שלב 2 + 3: עיבוד קונצנזוס, חישוב ציון והגדרת סטטוס שקוף (Reported Active)
    for code, data in code_consensus.items():
        source_count = len(data["sources"])
        score = 50 + (source_count * 25)
        
        processed_codes.append({
            "code": code,
            "reward": "Reported Community Reward",
            "status": "Reported Active",  # הפרדה ברורה מכך שאומת מול שרתי החברה
            "badge": "active",
            "source": f"Discovered from {source_count} source(s)",
            "observed_at": data["last_observed"],
            "score": score
        })

    # מיון לפי רמת הגיבוי והציון
    processed_codes.sort(key=lambda x: x["score"], reverse=True)

    # שלב 4: הפקת קובץ ה-JSON המעודכן
    output_data = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_discovered": len(processed_codes),
        "codes": processed_codes
    }

    filename = "roblox-codes.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved {len(processed_codes)} scraped codes to {filename}.")

if __name__ == "__main__":
    main()
