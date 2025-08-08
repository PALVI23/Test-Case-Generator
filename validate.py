
import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
import re
import json
from datetime import datetime

# --- Gemini API Key Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API key not found. Please set it in the .env file or directly in the script.")
genai.configure(api_key=GEMINI_API_KEY)

def get_validation_rules_from_llm(description):
    """Uses the LLM to parse the description and return a structured JSON of rules."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a rule extraction specialist. Analyze the following test case description and convert it into a structured JSON object.
    The JSON should only contain keys for the rules that are explicitly mentioned in the description.
    Possible keys are: data_type (String, Integer, Float, Date), length, format (e.g., YYYY-MM-DD), allowed_values (as a list), is_unique, not_null, is_numeric, is_alphanumeric.

    Description: "{description}"

    Return only the JSON object.
    """
    
    try:
        response = model.generate_content(prompt)
        if response.parts:
            json_text = ''.join(part.text for part in response.parts).strip()
            # Clean the response to get only the JSON
            json_text = json_text[json_text.find('{'):json_text.rfind('}') + 1]
            return json.loads(json_text)
    except Exception as e:
        print(f"Error parsing rules with LLM: {e}")
        return {}

def validate_data(formatted_dict_path, test_cases_path, output_path):
    """Validates the test data against LLM-parsed rules from the formatted dictionary."""
    df_formatted_dict = pd.read_csv(formatted_dict_path)
    df_test_cases = pd.read_excel(test_cases_path)

    validation_results = []
    test_id_counter = 1

    for r_idx, row_data in df_test_cases.iterrows():
        for col_name, cell_value in row_data.items():
            col_rules_row = df_formatted_dict[df_formatted_dict['field_name'] == col_name]
            if col_rules_row.empty:
                continue

            description = col_rules_row.iloc[0]['test_case_description']
            rules = get_validation_rules_from_llm(description)

            reasons = []
            # --- Validation Logic ---
            if not rules:
                reasons.append("Could not parse validation rules.")
            else:
                # Null Check
                if rules.get('not_null') and pd.isna(cell_value):
                    reasons.append("Value is null, but it must not be.")
                # Data Type and Format Validation
                elif not pd.isna(cell_value):
                    if rules.get('data_type') == 'Integer' and not isinstance(cell_value, int):
                        reasons.append(f"Expected an integer, but got '{cell_value}'.")
                    if rules.get('data_type') == 'Float' and not isinstance(cell_value, float):
                        reasons.append(f"Expected a float, but got '{cell_value}'.")
                    if rules.get('data_type') == 'Date':
                        try:
                            datetime.strptime(str(cell_value), rules.get('format', '%Y-%m-%d'))
                        except (ValueError, TypeError):
                            reasons.append(f"Expected date in {rules.get('format')} format, but got '{cell_value}'.")
                    if rules.get('allowed_values') and cell_value not in rules['allowed_values']:
                        reasons.append(f"Value '{cell_value}' is not in the allowed list: {rules['allowed_values']}.")
            
            status = "Failed" if reasons else "Passed"
            validation_results.append({
                'test_id': f'T{test_id_counter:04d}',
                'test_value': cell_value,
                'test_column': col_name,
                'description': f"{col_name} (Row {r_idx + 1}) - Validation Check",
                'status': status,
                'reason': "; ".join(reasons) if reasons else "Passed all checks."
            })
            test_id_counter += 1

    df_results = pd.DataFrame(validation_results)
    df_results.to_excel(output_path, index=False)

if __name__ == "__main__":
    formatted_dict_file = 'formatted_dictionary.csv'
    test_cases_file = 'input_data_try.xlsx'
    output_validation_file = 'validated_data.xlsx'
    validate_data(formatted_dict_file, test_cases_file, output_validation_file)
    print(f"Validation complete. Results saved to '{output_validation_file}'.")
