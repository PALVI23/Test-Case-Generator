

import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
import re

# --- Gemini API Key Configuration ---
load_dotenv()

# Get the Gemini API key from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API key not found. Please set it in the .env file or directly in the script.")

genai.configure(api_key=GEMINI_API_KEY)

def generate_formatted_dictionary(input_path, output_path):
    """
    Reads a data dictionary, processes it using a generative model,
    and creates a formatted dictionary with test case descriptions and examples.
    """
    # --- 1. Read Input Data Dictionary ---
    try:
        if input_path.endswith('.xlsx'):
            df_dict = pd.read_excel(input_path)
        elif input_path.endswith('.csv'):
            df_dict = pd.read_csv(input_path)
        else:
            raise ValueError("Unsupported file format. Please provide a .xlsx or .csv file.")
    except FileNotFoundError:
        print(f"Error: The file '{input_path}' was not found.")
        return

    # --- 2. Initialize Generative Model ---
    model = genai.GenerativeModel('gemini-1.5-flash')
    formatted_rows = []

    print("Processing data dictionary rows to generate formatted test cases...")

    # --- 3. Process Each Row ---
    for index, row in df_dict.iterrows():
        # Dynamically construct the Data Dictionary Entry part of the prompt
        data_dictionary_entry = "\n".join([f"- {col}: \"{row[col]}\"" for col in df_dict.columns])

        # Construct a detailed prompt for the LLM
        prompt = f"""
        You are a test case design assistant. Your task is to create a detailed, point-wise test case description and a set of example inputs (both valid and invalid) based on the provided data dictionary information.

        Data Dictionary Entry:
        {data_dictionary_entry}

        Instructions:
        1.  **Test Case Description**: Create a clear, point-wise description of all the rules a value in this column must follow. Combine all the provided details into a comprehensive checklist.
        2.  **Example Input**: Provide one clear valid example and one clear invalid example that violates one of the rules. The invalid example should be realistic.

        Output Format:
        Please provide the output in a single line, using "||" as a separator between the description and the examples.

        Test Case Description: [Your detailed, point-wise description here] || Example Input: Valid: [valid example] | Invalid: [invalid example with reason]
        """

        try:
            # Call the generative model
            response = model.generate_content(prompt)
            
            # --- 4. Parse the LLM Response ---
            if response.parts:
                generated_text = ''.join(part.text for part in response.parts)
                # Use regex for robust parsing of the two parts
                match = re.search(r"Test Case Description:(.*)\|\| Example Input:(.*)", generated_text, re.DOTALL)
                
                if match:
                    description = match.group(1).strip() if match.group(1) else ""
                    examples = match.group(2).strip() if match.group(2) else ""
                else:
                    # Fallback if regex fails, split by the separator
                    parts = generated_text.split('||')
                    description = parts[0].replace("Test Case Description:", "").strip() if len(parts) > 0 else "Description not generated."
                    examples = parts[1].replace("Example Input:", "").strip() if len(parts) > 1 else "Examples not generated."
            else:
                description = "No response text from model."
                examples = "No response text from model."

            # Append the structured data
            formatted_rows.append({
                'field_name': row[df_dict.columns[0]],
                'test_case_description': description,
                'example_input': examples
            })
            print(f"Successfully processed: {row[df_dict.columns[0]]}")

        except Exception as e:
            print(f"An error occurred while processing '{row[df_dict.columns[0]]}': {e}")
            # Add a placeholder row on error
            formatted_rows.append({
                'field_name': row[df_dict.columns[0]],
                'test_case_description': f'Error: {e}',
                'example_input': f'Error: {e}'
            })

    # --- 5. Create and Save the Formatted Dictionary ---
    df_formatted = pd.DataFrame(formatted_rows)
    df_formatted.to_csv(output_path, index=False)
    print(f"\nFile '{output_path}' created successfully.")


if __name__ == "__main__":
    # Define the input and output file paths
    input_data_dictionary = 'data_dictionary_types/data_dictionary_try1.xlsx'
    output_formatted_dictionary = 'formatted_dictionary.csv'
    
    # Run the process
    generate_formatted_dictionary(input_data_dictionary, output_formatted_dictionary)
