import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from db_helper import get_connection

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def get_match_data(driver):
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "event-row"))
    )
    rows = driver.find_elements(By.CSS_SELECTOR, "event-row")
    matches = []
    for row in rows:
        try:
            # Team names
            team_divs = row.find_elements(By.CSS_SELECTOR, ".event-names .event-team")
            if len(team_divs) < 2:
                continue
            home_team = team_divs[0].text.strip()
            away_team = team_divs[1].text.strip()
            if not home_team or not away_team:
                continue

            # 3-way market (Home/Draw/Away)
            market = row.find_element(By.CSS_SELECTOR, ".event-market.market-3-way")
            selections = market.find_elements(By.CSS_SELECTOR, ".event-selection")
            odds = {}
            for sel in selections:
                title = sel.get_attribute("title") or ""
                odd_text = sel.text.strip()
                if not odd_text:
                    continue
                try:
                    odd_val = float(odd_text)
                except ValueError:
                    continue
                if "home" in title.lower():
                    odds['home'] = odd_val
                elif "draw" in title.lower():
                    odds['draw'] = odd_val
                elif "away" in title.lower():
                    odds['away'] = odd_val
            if len(odds) == 3:
                matches.append({
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_odds': odds['home'],
                    'draw_odds': odds['draw'],
                    'away_odds': odds['away'],
                    'timestamp': datetime.now()
                })
        except Exception:
            continue
    return matches

def store_odds(matches):
    if not matches:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            for m in matches:
                # Check if match exists
                cur.execute("""
                    SELECT match_id FROM sportpesa_matches
                    WHERE home_team = %s AND away_team = %s
                """, (m['home_team'], m['away_team']))
                row = cur.fetchone()
                if row:
                    match_id = row['match_id']
                else:
                    # Insert new match
                    cur.execute("""
                        INSERT INTO sportpesa_matches (home_team, away_team, match_date)
                        VALUES (%s, %s, %s)
                        RETURNING match_id
                    """, (m['home_team'], m['away_team'], None))
                    inserted = cur.fetchone()
                    if inserted and 'match_id' in inserted:
                        match_id = inserted['match_id']
                    else:
                        print(f"Could not insert match: {m['home_team']} vs {m['away_team']}")
                        continue
                # Insert odds snapshot
                cur.execute("""
                    INSERT INTO sportpesa_odds_history
                    (match_id, recorded_at, home_odds, draw_odds, away_odds)
                    VALUES (%s, %s, %s, %s, %s)
                """, (match_id, m['timestamp'], m['home_odds'], m['draw_odds'], m['away_odds']))
            conn.commit()
    print(f"Stored {len(matches)} odds snapshots")

def main():
    driver = init_driver()
    url = "https://www.ke.sportpesa.com/en/sports-betting/football-1/"
    driver.get(url)
    time.sleep(8)  # let Angular render
    matches = get_match_data(driver)
    if matches:
        store_odds(matches)
    else:
        print("No matches extracted. Check selectors or page load.")
    driver.quit()

if __name__ == "__main__":
    main()