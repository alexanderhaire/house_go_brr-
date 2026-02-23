import json

def calculate_savings_timeline():
    with open("data/top_10_winners.json", "r") as f:
        data = json.load(f)
        
    salary = 70000
    current_savings = 3000
    
    # Let's realistically assume the user can save 15% of their gross monthly income 
    # strictly towards the house down payment if they are renting cheaply or living at home.
    # $70,000 / 12 = $5,833 gross * 0.15 = ~$875/month in savings.
    monthly_savings_rate = 875 
    
    print("\n=======================================================")
    print("FINANCIAL PROJECTION: SAVINGS TIMELINE VS. ALPHA CAPTURE")
    print("=======================================================")
    print(f"Current Assets: ${current_savings:,.0f}")
    print(f"Projected Savings Rate: ${monthly_savings_rate:,.0f}/mo (15% of Gross Income)")
    print("Goal: Maximize Alpha (Instant Equity) while moving FAST.")
    print("=======================================================\n")
    
    viable_targets = []
    
    for house in data:
        prop_type = house.get('property_type', 'Unknown')
        if prop_type in ['Manufactured', 'Mobile', 'Land']:
            continue
            
        price = house['price']
        # We assume they can get an FHA loan (3.5% down)
        required_down = price * 0.035
        # We also need to factor in closing costs (roughly 3% of the loan amount)
        # But for this aggressively optimized model, let's assume they negotiate "Seller Paid Closing Costs"
        
        shortfall = max(0, required_down - current_savings)
        months_to_save = shortfall / monthly_savings_rate if shortfall > 0 else 0
        
        viable_targets.append({
            "address": house.get("address", house.get("house_id")),
            "type": prop_type,
            "price": price,
            "required_down": required_down,
            "shortfall": shortfall,
            "months_to_save": months_to_save,
            "alpha": house['undervaluation_amount'],
            "alpha_pct": house['undervaluation_pct']
        })
        
    viable_targets = sorted(viable_targets, key=lambda x: x['months_to_save'])
    
    if not viable_targets:
        print("No viable non-manufactured homes in the current dataset.")
        return
        
    for target in viable_targets:
        print(f"TARGET: {target['address']} ({target['type']})")
        print(f"  Listed Price: ${target['price']:,.0f}")
        print(f"  Required Cash (3.5% Down): ${target['required_down']:,.0f}")
        print(f"  Current Shortfall: ${target['shortfall']:,.0f}")
        
        if target['months_to_save'] == 0:
            print(f"  TIMELINE: You can buy this TODAY.")
        else:
            print(f"  TIMELINE: {target['months_to_save']:.1f} months of saving.")
            
        print(f"  PAYOFF (Instant Equity): +${target['alpha']:,.0f} ({target['alpha_pct']:.1f}% Alpha)")
        # Calculate Return on Cash (Alpha / Required Down)
        roc = (target['alpha'] / target['required_down']) * 100
        print(f"  RETURN ON CASH: {roc:,.0f}%\n")

if __name__ == "__main__":
    calculate_savings_timeline()
