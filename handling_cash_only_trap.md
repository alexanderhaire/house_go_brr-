# The "Cash Only / Non-Warrantable" Trap

The user discovered that the mathematically optimal property (the $145k Condo on Arbor Pointe Cir) has a fatal flaw: The listing description explicitly states **"CASH ONLY!!!!!! COMPLEX DOES NOT QUALIFY FOR LOANS."**

This is why it has sat on the market for 1,271 days and why it is priced at a $60,000 discount to its statistical value. 

## The API Limitation
We previously determined that the **RentCast API does not provide the listing description** or any dedicated field indicating if a property is "Cash Only". We only have access to basic metadata (Price, Sqft, Year Built, Days on Market).

This means the engine literally cannot "read" that sentence to filter it out.

## How to Proceed
Since we cannot pull the description text to explicitly filter out "Cash Only" listings, we must rely entirely on the metadata footprint that these toxic listings leave behind.

### 1. The "Days on Market" Threshold Filter
The most obvious indicator of an un-financeable property is that it sits on the market forever. In a normal market, a fairly priced home sells in 30-90 days. 
- We should implement a hard cap on `days_on_market`. If a property has been listed for more than 180 days (6 months), it almost certainly has a fatal flaw (either it's a cash-only teardown, un-finishable, or tied up in probate). 
- **Action:** Update `main.py` or the evaluation engine to automatically discard any property with `days_on_market > 180`.

### 2. The Final Strategy
Because the API data is limited, the engine's purpose must be properly understood: It is an **anomaly detector**, not a blind purchasing bot.
- It is accurately finding properties that are statistically priced far below their physical characteristics. 
- However, when a property is *that* undervalued, there is usually a human reason that isn't in the raw API data (like an un-financeable HOA).
- The engine's job is to surface the Top 10 anomalies, and the human's job is to spend 30 seconds reading the Zillow description to see *why* it's an anomaly.

### Next Steps for the User
If the user wants to expand their search to find *financeable* options with their $3,000 / $5,500 down payment, we need to:
1. Hardcode a `days_on_market < 180` filter.
2. Hardcode an exclusion for `Manufactured` and `Land` properties.
3. Radically expand the search radius or the total number of listings fetched from RentCast (currently capped at 50) to find the rare, financeable needle in the haystack.
