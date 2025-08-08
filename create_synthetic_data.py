import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
import re
import numpy as np
import random
import sys

# --- Gemini API Key Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API key not found. Please set it in the .env file or directly in the script.")
genai.configure(api_key=GEMINI_API_KEY)

def create_invalidation_plan(num_rows, num_cols, min_invalid_per_row, min_invalid_per_col, target_invalid_fraction):
    """
    Creates a plan for which cells in a grid should be invalid to meet the specified constraints.
    """
    # Start with a random plan
    plan = np.random.rand(num_rows, num_cols) < target_invalid_fraction
    
    # Ensure minimum invalid values per row
    for i in range(num_rows):
        if np.sum(plan[i, :]) < min_invalid_per_row:
            invalid_indices = np.random.choice(num_cols, min_invalid_per_row, replace=False)
            plan[i, invalid_indices] = True
            
    # Ensure minimum invalid values per column
    for j in range(num_cols):
        if np.sum(plan[:, j]) < min_invalid_per_col:
            invalid_indices = np.random.choice(num_rows, min_invalid_per_col, replace=False)
            plan[invalid_indices, j] = True
            
    return plan

def generate_synthetic_data(formatted_dict_path, output_path, num_records=50, min_invalid_per_row=4, min_invalid_per_col=10):
    """
    Generates synthetic data based on a detailed plan, ensuring a mix of valid and invalid data
    that meets the specified row and column constraints.
    """
    # --- 1. Read the Formatted Dictionary ---
    try:
        df_formatted_dict = pd.read_csv(formatted_dict_path)
    except FileNotFoundError:
        print(f"Error: The file '{formatted_dict_path}' was not found.")
        return

    # --- 2. Initialize Generative Model ---
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # --- 3. Create Invalidation Plan ---
    num_cols = len(df_formatted_dict)
    target_invalid_fraction = 0.5  # Aim for a 50/50 split
    invalidation_plan = create_invalidation_plan(num_records, num_cols, min_invalid_per_row, min_invalid_per_col, target_invalid_fraction)
    
    # --- 4. Generate Data Cell by Cell ---
    all_data = []
    print("Generating synthetic data with constraints...")

    for i in range(num_records):
        row_data = {}
        for j, field_row in df_formatted_dict.iterrows():
            field_name = field_row['field_name']
            description = field_row['test_case_description']
            
            # Determine if the cell should be valid or invalid based on the plan
            is_invalid = invalidation_plan[i, j]
            
            # Construct the prompt
            if is_invalid:
                prompt = f"Based on these rules: {description}. Generate a single, logically invalid data value that realistically breaks one of the rules. Provide only the value itself, with no extra explanation."
            else:
                prompt = f"Based on these rules: {description}. Generate a single, valid data value. Provide only the value itself, with no extra explanation."

            try:
                response = model.generate_content(prompt)
                if response.parts:
                    generated_value = ''.join(part.text for part in response.parts).strip()
                    row_data[field_name] = generated_value
                else:
                    row_data[field_name] = "GENERATION_ERROR"
                    
            except Exception as e:
                print(f"An error occurred while generating data for '{field_name}': {e}")
                row_data[field_name] = "API_ERROR"
        
        all_data.append(row_data)
        print(f"Generated row {i + 1}/{num_records}")

    # --- 5. Create and Save the DataFrame ---
    df_synthetic = pd.DataFrame(all_data)
    df_synthetic.to_excel(output_path, index=False)
    print(f"\nFile '{output_path}' created successfully with constrained synthetic data.")


if __name__ == "__main__":
    # Define the input and output file paths
    formatted_dictionary_file = 'formatted_dictionary.csv'
    output_test_cases_file = 'input_data_try.xlsx'

    # Parse command-line arguments
    if len(sys.argv) > 3:
        num_records_arg = int(sys.argv[1])
        min_invalid_per_row_arg = int(sys.argv[2])
        min_invalid_per_col_arg = int(sys.argv[3])
    else:
        # Default values if not provided (should not happen when called from app.py)
        num_records_arg = 50
        min_invalid_per_row_arg = 4
        min_invalid_per_col_arg = 10
    
    # Run the data generation process with parsed arguments
    generate_synthetic_data(formatted_dictionary_file, output_test_cases_file, 
                            num_records=num_records_arg, 
                            min_invalid_per_row=min_invalid_per_row_arg, 
                            min_invalid_per_col=min_invalid_per_col_arg)
