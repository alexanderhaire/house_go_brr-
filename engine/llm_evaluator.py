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
        Takes property metadata and asks GPT-4o to generate a qualitative repair cost estimate in dollars.
        Returns a dict with `repair_cost_estimate` (int) and `reasoning` (str).
        """
        if not self.client:
            return {"repair_cost_estimate": 0, "reasoning": "No OpenAI API key provided."}

        system_prompt = """
You are an expert real estate investor and flipper. 
Your job is to analyze property metadata, especially the listing description, and determine if the property is likely a "turnkey" ready-to-move-in home ($0 repair cost) or a "fixer-upper" requiring significant capital expenditure.
Estimate the absolute dollar amount of repairs needed to bring the property to market standard.
If the description mentions "TLC", "investor special", "as-is", or it's very old without recent updates, estimate a higher cost (e.g. $20k - $100k+).

Respond strictly with a JSON object in the following format:
{
    "repair_cost_estimate": 25000, 
    "reasoning": "A concise 1-sentence explanation of why you estimated this repair cost."
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
- Public Description: {property_data.get('description', 'Not provided')}
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
            
            # Default to 0 if there's an issue parsing
            repair_cost = int(result.get("repair_cost_estimate", 0))
            reasoning = result.get("reasoning", "No clear reasoning provided.")
            
            return {
                "repair_cost_estimate": repair_cost,
                "reasoning": reasoning
            }
            
        except Exception as e:
            print(f"LLM Evaluation failed: {e}")
            return {"repair_cost_estimate": 0, "reasoning": f"LLM evaluation failed: {e}"}
