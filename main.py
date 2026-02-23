from engine.discovery_engine import UndervaluationEngine
from engine.api_client import RentCastClient
import pandas as pd
import numpy as np
import requests
import json
import time
from datetime import datetime

import os
# You can move this to config.py later if you prefer
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1475344856501981294/U1Ayd3EJAQuLzA5AWsRZOIsUiVQ6Ken9JjQxMIC2Q8o5-9MrPn5RsLQgoHydG2VGQv5i")

def print_financial_advice():
    print("\n" + "="*50)
    print("FINANCIAL ADVICE: EQUITY VS. SUNK COSTS")
    print("="*50)
    print("1. HOUSE EQUITY: Principal payments are RECOVERABLE wealth.")
    print("2. HOA FEES: These are SUNK COSTS (like rent) that never return.")
    print("3. BUYING POWER LOSS: Every $1 in HOA fee reduces your potential")
    print("   mortgage principal by ~$150. A $500 HOA fee 'costs' you")
    print("   roughly $75,000 in home-buying power.")
    print("\nPRO TIP: Focus on 'Alpha' homes with LOW or NO HOA fees to")
    print("maximize the ratio of wealth-building to sunk-cost spending.")

def send_discord_alert(gem_df, is_new_champ=False, reason=""):
    """
    Sends a formatted alert to Discord for the Champion property.
    """
    if not DISCORD_WEBHOOK_URL:
        return

    row = gem_df.iloc[0] # We only send the top 1

    # Format the numbers
    price_str = f"${row['price']:,.0f}"
    market_val_str = f"${row['predicted_price']:,.0f}"
    alpha_str = f"{row['undervaluation_pct']:.1f}%"
    mortgage_str = f"${row['monthly_mortgage']:,.0f}/mo"
    hoa_str = f"${row['hoa_fee']:,.0f}/mo"
    tax_ins_str = f"${row['monthly_tax_ins']:,.0f}/mo"
    total_monthly = row['total_monthly_cost']
    total_str = f"${total_monthly:,.0f}/mo"

    title_prefix = "🏆 NEW CHAMPION:" if is_new_champ else "🚨 NEW GEM:"

    embed = {
        "title": f"{title_prefix} {alpha_str} Undervalued",
        "description": f"The #1 Best Deal currently on the market in Tampa ({row['neighborhood_name']})!\n{reason}\n*Evaluated at 100% Debt Financing (6% Market Rate)*",
        "color": 5814783, # A nice green color
        "fields": [
            {"name": "Address", "value": row['address'], "inline": False},
            {"name": "Listed Price", "value": price_str, "inline": True},
            {"name": "AI Fair Value", "value": market_val_str, "inline": True},
            {"name": "Alpha Score", "value": alpha_str, "inline": True},
            {"name": "Est. Mortgage (6%)", "value": mortgage_str, "inline": True},
            {"name": "HOA Fee", "value": hoa_str, "inline": True},
            {"name": "Taxes & Ins.", "value": tax_ins_str, "inline": True},
            {"name": "TOTAL Carrying Cost", "value": f"**{total_str}**", "inline": True}
        ],
        "footer": {"text": "Undervalued Home Discovery Engine • Continuous Scanner"}
    }

    payload = {
        "content": f"🏆 **New Champion Alert** in {row['neighborhood_name']}! ({row['address']} for {price_str})",
        "embeds": [embed]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            print(f"  -> Successfully sent Discord alert for {row['address']}")
        else:
            print(f"  -> Failed to send Discord alert: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"  -> Error sending Discord alert: {e}")
    
    # Sleep slightly to avoid Discord rate limits
    time.sleep(1)



CHAMPION_FILE = "data/current_champion.json"

def load_champion():
    if os.path.exists(CHAMPION_FILE):
        try:
            with open(CHAMPION_FILE, 'r') as f:
                data = json.load(f)
                return data.get('house_id')
        except:
            return None
    return None

def save_champion(house_id):
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    with open(CHAMPION_FILE, 'w') as f:
        json.dump({'house_id': house_id}, f)

def main():
    print("="*50)
    print("HOUSE DISCOVERY ENGINE: DAEMON MODE STARTING")
    print("="*50)
    
    # 1. Initialize & Train (Done ONCE)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Booting Engine & Training Memory Models...")
    historical_data_path = "data/housing_data_tampa.csv"
    engine = UndervaluationEngine(data_path=historical_data_path)
    engine.run_pipeline()
    
    
    rentcast_api_key = os.getenv("RENTCAST_API_KEY", "8efdc915106b4bce818b259f9af58484")
    client = RentCastClient(rentcast_api_key)
    
    # State tracking
    seen_house_ids = set()
    
    # Load champion from persistent storage so Railway restarts don't trigger duplicate alerts
    current_champion_id = load_champion()
    if current_champion_id:
        print(f"Successfully loaded previous champion from memory: {current_champion_id}")
    
    # SECURITY: The RentCast Free Tier only allows 50 requests per month.
    # To stay safe, we scan once every 15 hours. 
    # (30 days * 24 hours / 15 = 48 requests/month)
    scan_interval_seconds = 60 * 60 * 15
    
    print("\n==================================================")
    print("DAEMON ONLINE: Scanning market for the Champion Home")
    print("==================================================")
    
    while True:
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{timestamp}] Fetching latest active listings...")
            
            # 2. Fetch Live Candidates
            live_listings_df = client.fetch_listings(city="Tampa", state="FL", limit=50) # Increased limit
            
            if live_listings_df.empty:
                print(f"[{timestamp}] No active listings returned by API. Sleeping...")
                time.sleep(scan_interval_seconds)
                continue
                
            # Track newly found listings for logging purposes
            new_listings_df = live_listings_df[~live_listings_df['house_id'].isin(seen_house_ids)]
            if not new_listings_df.empty:
                print(f"[{timestamp}] Found {len(new_listings_df)} NEW listings. Evaluating total market...")
                seen_house_ids.update(new_listings_df['house_id'].tolist())
            else:
                print(f"[{timestamp}] Scanned {len(live_listings_df)} listings. 0 new. Re-evaluating market...")
            
            # 3. Evaluate ALL candidates to find the current Champion
            evaluated_df = engine.evaluate_candidates(live_listings_df, top_n=len(live_listings_df))
            
            if evaluated_df.empty:
                print(f"[{timestamp}] Evaluated properties but result was empty. Sleeping...")
                time.sleep(scan_interval_seconds)
                continue

            current_best = evaluated_df.iloc[0]
            best_id = current_best['house_id']
            
            if current_champion_id is None:
                # First run - Establish initial champion
                current_champion_id = best_id
                save_champion(best_id)
                print("\n" + "🏆"*20)
                print(f"INITIAL MARKET CHAMPION ESTABLISHED: {current_best['address']}")
                print("🏆"*20)
                reason = "_Initial Scan - Best property currently available._"
                send_discord_alert(evaluated_df.head(1), is_new_champ=True, reason=reason)
                
            elif best_id != current_champion_id:
                # Champion changed!
                print("\n" + "🏆"*20)
                print(f"CHAMPION OVERTHROWN!")
                print("🏆"*20)
                
                if current_champion_id not in live_listings_df['house_id'].values:
                    reason = "*Previous champion sold/delisted - falling to next in line.*"
                else:
                    reason = "*New property dethroned the previous champion!*"
                
                print(f"Reason: {reason}")
                print(f"New Champion: {current_best['address']} (Alpha: {current_best['undervaluation_pct']:.1f}%)")
                
                current_champion_id = best_id
                save_champion(best_id)
                send_discord_alert(evaluated_df.head(1), is_new_champ=True, reason=reason)
                
            else:
                print(f"[{timestamp}] Champion holding strong: {current_best['address']} (Alpha: {current_best['undervaluation_pct']:.1f}%)")

            # Always save the Top 10 Leaderboard to a JSON file (Information Engine Feature)
            top_10_df = evaluated_df.head(10).copy()
            # Convert datetime columns to string before exporting to JSON
            if 'date' in top_10_df.columns:
                 top_10_df['date'] = top_10_df['date'].astype(str)
                 
            top_10_json_path = "data/top_10_winners.json"
            top_10_df.to_json(top_10_json_path, orient='records', indent=4)
            print(f"[{timestamp}] Top 10 Leaderboard saved to {top_10_json_path}")

            # Always print the current champion stats to terminal just so we can see it
            display_df = evaluated_df.head(1)[['address', 'neighborhood_name', 'price', 'predicted_price', 'monthly_mortgage', 'hoa_fee', 'monthly_tax_ins', 'total_monthly_cost', 'undervaluation_pct']]
            display_df = display_df.rename(columns={
                'address': 'Address',
                'neighborhood_name': 'Zip/Area',
                'price': 'Listed Price',
                'predicted_price': 'Market Val',
                'monthly_mortgage': 'Est. Mtg (6%)',
                'hoa_fee': 'HOA/mo',
                'monthly_tax_ins': 'Tax&Ins/mo',
                'total_monthly_cost': 'Total Cost/mo',
                'undervaluation_pct': 'Alpha %'
            })
            
            cols_to_format = ['Listed Price', 'Market Val', 'Est. Mtg (6%)', 'HOA/mo', 'Tax&Ins/mo', 'Total Cost/mo']
            for col in cols_to_format:
                display_df[col] = display_df[col].map('${:,.0f}'.format)
            
            print("\nLeaderboard (Current Champion):")
            print(display_df.to_string(index=False))
            print_financial_advice()
                
            # Sleep until next cycle
            time.sleep(scan_interval_seconds)
            
        except KeyboardInterrupt:
            print("\nShutting down discovery daemon. Goodbye!")
            break
        except Exception as e:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ERROR during scan cycle: {e}")
            print(f"Retrying in {scan_interval_seconds} seconds...")
            time.sleep(scan_interval_seconds)

if __name__ == "__main__":
    main()
