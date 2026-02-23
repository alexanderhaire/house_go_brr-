import os
import json
from openai import OpenAI

class LLMPropertyEvaluator:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def evaluate_property(self, property_data):
        """
        Takes property metadata and asks GPT-4o to generate a qualitative risk multiplier.
        Returns a dict with `risk_multiplier` (float 0.5 - 1.0) and `reasoning` (str).
        """
        if not self.client:
            return {"risk_multiplier": 1.0, "reasoning": "No OpenAI API key provided."}

        system_prompt = """
You are an expert real estate investor and flipper. 
Your job is to analyze property metadata and determine if the property is likely a "turnkey" ready-to-move-in home (Multiplier 1.0) or a "fixer-upper/gut job" requiring significant capital expenditure (Multiplier closer to 0.7 or lower).
If the property has been on the market for a long time (e.g., > 60 days) in a hot market, or is very old without recent updates, it's likely a fixer-upper.

Respond strictly with a JSON object in the following format:
{
    "risk_multiplier": 0.85, 
    "reasoning": "A concise 1-sentence explanation of why you chose this multiplier."
}
"""
        
        user_prompt = f"""
Please evaluate the following property for hidden risk / condition issues:
- Address: {property_data.get('address')}
- Area/Zip: {property_data.get('neighborhood_name')}
- Property Type: {property_data.get('property_type', 'Unknown')}
- Asking Price: ${property_data.get('price')}
- Sqft: {property_data.get('sqft')}
- Beds/Baths: {property_data.get('beds')}/{property_data.get('baths')}
- Year Built: {property_data.get('year_built', 'Unknown')}
- Days on Market: {property_data.get('days_on_market', 'Unknown')}
- HOA Fee: ${property_data.get('hoa_fee', 0)}/mo
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={ "type": "json_object" },
                temperature=0.2
            )
            
            result_str = response.choices[0].message.content
            result = json.loads(result_str)
            
            # Bound the multiplier between 0.5 and 1.0 to prevent crazy outputs
            multiplier = max(0.5, min(1.0, float(result.get("risk_multiplier", 1.0))))
            reasoning = result.get("reasoning", "No clear reasoning provided.")
            
            return {
                "risk_multiplier": multiplier,
                "reasoning": reasoning
            }
            
        except Exception as e:
            print(f"LLM Evaluation failed: {e}")
            return {"risk_multiplier": 1.0, "reasoning": f"LLM evaluation failed: {e}"}
