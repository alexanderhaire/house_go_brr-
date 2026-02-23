import json
import os

def check_affordability(property_price, yearly_salary_gross, max_down_payment):
    gross_monthly = yearly_salary_gross / 12
    max_monthly_total_debt = gross_monthly * 0.43 
    required_down_payment_fha = property_price * 0.035
    required_down_payment_conv = property_price * 0.03
    
    return {
        "gross_monthly_income": gross_monthly,
        "max_allowable_dti_payment": max_monthly_total_debt,
        "fha_down_payment": required_down_payment_fha,
        "conv_down_payment": required_down_payment_conv,
        "can_afford_down_fha": required_down_payment_fha <= max_down_payment,
        "can_afford_down_conv": required_down_payment_conv <= max_down_payment
    }

def analyze():
    with open("data/top_10_winners.json", "r") as f:
        data = json.load(f)
        
    salary = 70000
    down = 3000
    
    print(f"--- FINANCIAL CONSTRAINTS ---")
    print(f"Salary: ${salary:,.0f} / year")
    print(f"Max Down Payment: ${down:,.0f}")
    
    viable_homes = []
    
    for house in data:
        # FILTER 1: Exclude Manufactured Homes. 
        # As you discovered, they are frequently in 55+ parks and have hidden "Lot Rents" 
        # (like the $89/mo promo in your screenshot) which destroy the equity creation model.
        if house.get('property_type') in ['Manufactured', 'Mobile']:
            print(f"Skipping {house.get('address', house.get('house_id'))} (Reason: Manufactured/55+ Risk)")
            continue
            
        # FILTER 2: Exclude Vacant Land. You can't live there easily and standard FHA/Conv loans don't apply.
        if house.get('property_type') == 'Land':
            print(f"Skipping {house.get('address', house.get('house_id'))} (Reason: Vacant Land)")
            continue
            
        stats = check_affordability(house['price'], salary, down)
        
        # Consider homes we can afford the down payment on 
        # (even if it's slightly over, we can negotiate the price down!)
        # Let's look for homes priced under $110,000 where we could aggressively negotiate down to $100k.
        if house['price'] <= 110000 and house['total_monthly_cost'] <= stats['max_allowable_dti_payment']:
            viable_homes.append({
                "address": house.get("address", house.get("house_id")),
                "price": house['price'],
                "undervaluation": house['undervaluation_amount'],
                "alpha_pct": house['undervaluation_pct'],
                "monthly_cost": house['total_monthly_cost'],
                "down_3pct": stats['conv_down_payment'],
                "dti": (house['total_monthly_cost'] / stats['gross_monthly_income']) * 100,
                "type": house.get('property_type')
            })
            
    viable_homes = sorted(viable_homes, key=lambda x: x['alpha_pct'], reverse=True)
    
    print(f"\n--- VIABLE HOMES FOUND: {len(viable_homes)} ---")
    for idx, vh in enumerate(viable_homes):
        print(f"\nRank #{idx+1}: {vh['address']} ({vh['type']})")
        print(f"  Listed Price: ${vh['price']:,.0f} (Need to negotiate down to $100k for 3% down = $3k limit)")
        print(f"  Down Payment if bought at $100k: $3,000")
        print(f"  Total PITI+HOA (approx): ${vh['monthly_cost']:,.0f}/mo")
        print(f"  DTI Ratio: {vh['dti']:.1f}% (Max 43%)")
        print(f"  Instant Equity Creation: ${vh['undervaluation']:,.0f}")
        print(f"  Alpha Score: {vh['alpha_pct']:.1f}%")
        
    if not viable_homes:
        print("\nNo viable Single Family/Condos found under the budget constraint in the current Top 10.")
        print("Recommendation: You need to expand the search radius, increase the limit on RentCast, or look for FHA Down Payment Assistance programs (which can cover the 3.5% down for you).")

if __name__ == "__main__":
    analyze()
