from engine.discovery_engine import UndervaluationEngine
from engine.api_client import RentCastClient
import pandas as pd
import numpy as np
import config
import requests
import json
import time
from datetime import datetime

# You can move this to config.py later if you prefer
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1475344856501981294/U1Ayd3EJAQuLzA5AWsRZOIsUiVQ6Ken9JjQxMIC2Q8o5-9MrPn5RsLQgoHydG2VGQv5i"

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

def send_discord_alert(gem_df):
    """
    Sends a formatted alert to Discord for newly discovered undervalued properties.
    """
    if not DISCORD_WEBHOOK_URL:
        return

    for _, row in gem_df.iterrows():
        # Format the numbers
        price_str = f"${row['price']:,.0f}"
        market_val_str = f"${row['predicted_price']:,.0f}"
        alpha_str = f"{row['undervaluation_pct']:.1f}%"
        mortgage_str = f"${row['monthly_mortgage']:,.0f}/mo"
        hoa_str = f"${row['hoa_fee']:,.0f}/mo"
        total_monthly = row['monthly_mortgage'] + row['hoa_fee']
        total_str = f"${total_monthly:,.0f}/mo"

        embed = {
            "title": f"🚨 NEW HIGH-ALPHA GEM: {alpha_str} Undervalued",
            "description": f"Found a new highly undervalued property in Tampa ({row['neighborhood_name']})!\n*Evaluated at 100% Debt Financing (6% Market Rate)*",
            "color": 5814783, # A nice green color
            "fields": [
                {"name": "Address", "value": row['address'], "inline": False},
                {"name": "Listed Price", "value": price_str, "inline": True},
                {"name": "AI Fair Value", "value": market_val_str, "inline": True},
                {"name": "Alpha Score", "value": alpha_str, "inline": True},
                {"name": "Est. Mortgage (6%)", "value": mortgage_str, "inline": True},
                {"name": "HOA Fee", "value": hoa_str, "inline": True},
                {"name": "TOTAL Carrying Cost", "value": f"**{total_str}**", "inline": True}
            ],
            "footer": {"text": "Undervalued Home Discovery Engine • Continuous Scanner"}
        }

        payload = {
            "content": f"🏠 **New Gem Alert** in {row['neighborhood_name']}! ({row['address']} for {price_str})",
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

def main():
    print("="*50)
    print("HOUSE DISCOVERY ENGINE: DAEMON MODE STARTING")
    print("="*50)
    
    # 1. Initialize & Train (Done ONCE)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Booting Engine & Training Memory Models...")
    historical_data_path = "data/housing_data_tampa.csv"
    engine = UndervaluationEngine(data_path=historical_data_path)
    engine.run_pipeline()
    
    client = RentCastClient(config.RENTCAST_API_KEY)
    
    # State tracking
    seen_house_ids = set()
    scan_interval_seconds = 60 * 5 # Scan every 5 minutes
    
    print("\n==================================================")
    print("DAEMON ONLINE: Scanning market for High-Alpha Gems")
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
                
            # Filter to only NEW listings we haven't processed
            new_listings_df = live_listings_df[~live_listings_df['house_id'].isin(seen_house_ids)]
            
            if new_listings_df.empty:
                print(f"[{timestamp}] Scanned {len(live_listings_df)} listings. 0 new. Sleeping...")
                time.sleep(scan_interval_seconds)
                continue
                
            print(f"[{timestamp}] Found {len(new_listings_df)} NEW listings! Evaluating Alpha scores...")
            
            # 3. Evaluate ONLY new candidates against models
            evaluated_df = engine.evaluate_candidates(new_listings_df, top_n=len(new_listings_df))
            
            # Update seen state
            seen_house_ids.update(new_listings_df['house_id'].tolist())
            
            # Filter for "Gems" (Alpha > 10%)
            gems = evaluated_df[evaluated_df['undervaluation_pct'] >= 10.0].copy()
            
            if gems.empty:
                print(f"[{timestamp}] Evaluated {len(new_listings_df)} properties. No high-alpha gems found. Sleeping...")
            else:
                # WE FOUND GEMS! Alert the user.
                print("\n" + "🚨"*20)
                print(f"NEW UNDERVALUED GEMS DISCOVERED! ({len(gems)} found)")
                print("🚨"*20)
                
                # Send Discord Alerts
                print("Sending alerts to Discord webhook...")
                send_discord_alert(gems)
                
                # Formatting
                pd.set_option('display.max_columns', None)
                pd.set_option('display.width', 1000)
                
                display_df = gems[['address', 'neighborhood_name', 'price', 'predicted_price', 'monthly_mortgage', 'hoa_fee', 'total_monthly_cost', 'undervaluation_pct']]
                display_df = display_df.rename(columns={
                    'address': 'Address',
                    'neighborhood_name': 'Zip/Area',
                    'price': 'Listed Price',
                    'predicted_price': 'Market Val',
                    'monthly_mortgage': 'Est. Mtg (6%)',
                    'hoa_fee': 'HOA/mo',
                    'total_monthly_cost': 'Total Cost/mo',
                    'undervaluation_pct': 'Alpha %'
                })
                
                display_df = display_df.sort_values('Alpha %', ascending=False)
                
                cols_to_format = ['Listed Price', 'Market Val', 'Est. Mtg (6%)', 'HOA/mo', 'Total Cost/mo']
                for col in cols_to_format:
                    display_df[col] = display_df[col].map('${:,.0f}'.format)
                
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
