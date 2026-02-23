import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_synthetic_data(num_houses=1000, num_neighborhoods=10, history_days=365):
    """
    Generates synthetic real estate data with time-series trends and local clusters in Tampa.
    """
    np.random.seed(42)
    
    # Tampa bounds: Lat ~27.8 to 28.1, Long ~ -82.6 to -82.3
    tampa_bounds = {
        'lat': (27.8, 28.1),
        'long': (-82.6, -82.3)
    }

    # Common street names in Tampa area
    streets = [
        "Bayshore Blvd", "Kennedy Blvd", "Dale Mabry Hwy", "Nebraska Ave", 
        "Florida Ave", "Hyde Park Ave", "Howard Ave", "MacDill Ave",
        "Gandy Blvd", "Fowler Ave", "Busch Blvd", "Ybor St", "Seventh Ave",
        "Westshore Blvd", "Hillsborough Ave", "Bearss Ave", "Bruce B Downs Blvd"
    ]
    
    # 1. Define Neighborhoods
    neighborhoods = []
    neighborhood_names = ["South Tampa", "Ybor City", "Hyde Park", "Seminole Heights", 
                          "Westchase", "New Tampa", "Carrollwood", "Brandon", 
                          "Temple Terrace", "Town 'n' Country"]
    
    for i in range(num_neighborhoods):
        neighborhoods.append({
            'id': i,
            'name': neighborhood_names[i] if i < len(neighborhood_names) else f"Neighborhood {i}",
            'lat': np.random.uniform(tampa_bounds['lat'][0], tampa_bounds['lat'][1]),
            'long': np.random.uniform(tampa_bounds['long'][0], tampa_bounds['long'][1]),
            'quality_multiplier': np.random.uniform(1.0, 2.5), # Tampa premium areas
            'appreciation_rate': np.random.uniform(0.00015, 0.0004) # Higher growth in FL
        })
    
    data = []
    
    # 2. Generate Houses
    for i in range(num_houses):
        nb = np.random.choice(neighborhoods)
        
        # House characteristics
        # Support smaller units (Condos/Studios) down to 400 sqft
        sqft = np.random.normal(1800, 800)
        sqft = max(450, sqft)
        
        beds = int(sqft / 600) + np.random.randint(0, 2)
        beds = max(1, beds)
        
        baths = max(1, int(beds * 0.7 + np.random.uniform(0, 1)))
        
        # Base price calculation (Tampa market ~ $200-$450/sqft base)
        # Smaller units often have HIGHER price per sqft but lower absolute price
        sqft_premium = 1.0 if sqft > 1000 else 1.2
        base_price_per_sqft = 220 * nb['quality_multiplier'] * sqft_premium
        initial_price = sqft * base_price_per_sqft
        
        # Random noise in base price
        initial_price *= np.random.uniform(0.85, 1.15)
        
        # House ID and Fake Address
        house_id = f"TPA{i:04d}"
        address = f"{np.random.randint(100, 9999)} {np.random.choice(streets)}"
        
        # HOA fee generation: higher quality or specific neighborhoods have higher fees
        # Some homes have no HOA (0), others range from $50 to $600+
        has_hoa = np.random.choice([True, False], p=[0.7, 0.3])
        if has_hoa:
            base_hoa = 50 * nb['quality_multiplier']
            hoa_fee = base_hoa + np.random.uniform(0, 300)
        else:
            hoa_fee = 0
            
        # Local coordinates near neighborhood centroid
        lat = nb['lat'] + np.random.normal(0, 0.015)
        long = nb['long'] + np.random.normal(0, 0.015)
        
        # 3. Generate Time-Series History
        start_date = datetime.now() - timedelta(days=history_days)
        num_events = np.random.randint(2, 5)
        event_dates = sorted([start_date + timedelta(days=np.random.randint(0, history_days)) for _ in range(num_events)])
        
        for date in event_dates:
            days_passed = (date - start_date).days
            current_market_price = initial_price * (1 + nb['appreciation_rate'] * days_passed)
            
            # Listing price noise
            listing_price = current_market_price * np.random.uniform(0.97, 1.03)
            
            data.append({
                'house_id': house_id,
                'address': address,
                'neighborhood_id': nb['id'],
                'neighborhood_name': nb['name'],
                'lat': lat,
                'long': long,
                'sqft': sqft,
                'beds': beds,
                'baths': baths,
                'hoa_fee': hoa_fee,
                'date': date,
                'price': listing_price,
                'is_undervalued': False
            })

    # 4. Inject "Undervalued" Gems (Recently)
    df = pd.DataFrame(data)
    unique_houses = df['house_id'].unique()
    undervalued_count = max(1, int(len(unique_houses) * 0.015))
    undervalued_houses = np.random.choice(unique_houses, undervalued_count, replace=False)
    
    for house_id in undervalued_houses:
        latest_idx = df[df['house_id'] == house_id]['date'].idxmax()
        # 20% to 35% discount
        df.at[latest_idx, 'price'] *= np.random.uniform(0.65, 0.8)
        df.at[latest_idx, 'is_undervalued'] = True

    return df

if __name__ == "__main__":
    print("Generating synthetic Tampa real estate data...")
    df = generate_synthetic_data()
    
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/housing_data_tampa.csv", index=False)
    
    print(f"Generated {len(df)} records for {df['house_id'].nunique()} houses in Tampa.")
    print(f"Data saved to data/housing_data_tampa.csv")
    print("\nSample of Tampa listings:")
    print(df[['house_id', 'address', 'neighborhood_name', 'price']].tail(10))
