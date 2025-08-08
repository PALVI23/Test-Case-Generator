import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
import sys

# --- Gemini API Key Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API key not found. Please set it in the .env file or directly in the script.")
genai.configure(api_key=GEMINI_API_KEY)

def incorporate_feedback(original_dict_path, feedback_text, output_path):
    """Incorporates user feedback into the formatted data dictionary."""
    df_original = pd.read_csv(original_dict_path)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    updated_rows = []

    for index, row in df_original.iterrows():
        prompt = f"""
        You are a test case design assistant. Your task is to refine the test case description and examples for the field '{row['field_name']}' based on the user's feedback.

        Original Description: {row['test_case_description']}
        User Feedback: "{feedback_text}"

        Instructions:
        - Update the description to be a numbered list of clear, concise rules for the '{row['field_name']}' field.
        - Provide a single, clear example of a valid and an invalid input for the '{row['field_name']}' field, with a brief reason for the invalid case.
        - Return the new description and examples in the following format:
          Test Case Description: [new description] || Example Input: [new examples]

        Example of the desired output format for a field named 'region':
        Test Case Description: 1. The 'region' field must be a string. 2. The 'region' field must contain one of the following values: "North", "South", "East", "West". 3. The 'region' field must not contain any leading or trailing whitespace. 4. The 'region' field must not be NULL or empty. 5. The 'region' field must not contain any special characters or numbers. || Example Input: Valid: North | Invalid: Northeast (Reason: Value "Northeast" is not in the allowed list)
        """
        
        try:
            response = model.generate_content(prompt)
            if response.parts:
                # Simple parsing, assuming the LLM follows the format
                parts = ''.join(part.text for part in response.parts).split('||')
                description = parts[0].replace("Test Case Description:", "").strip()
                examples = parts[1].replace("Example Input:", "").strip()
                
                updated_rows.append({
                    'field_name': row['field_name'],
                    'test_case_description': description,
                    'example_input': examples
                })
            else:
                # If feedback incorporation fails, keep the original
                updated_rows.append(row.to_dict())
        except Exception:
            updated_rows.append(row.to_dict())

    df_updated = pd.DataFrame(updated_rows)
    df_updated.to_csv(output_path, index=False)

if __name__ == "__main__":
    # This script is designed to be called from the main app
    # with the file paths and feedback as arguments.
    if len(sys.argv) > 2:
        original_file = sys.argv[1]
        feedback = sys.argv[2]
        output_file = sys.argv[3]
        incorporate_feedback(original_file, feedback, output_file)
