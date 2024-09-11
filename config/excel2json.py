import pandas as pd
import os
import json

# Load the Excel file
excel_file_path = 'config/config.xlsx'         # Python function list for self-correction
df = pd.read_excel(excel_file_path)

# Initialize an empty list to store the data for JSON
data_list = []

# Iterate through each row in the dataframe
for index, row in df.iterrows():

    # Create a dictionary for the current row
    row_data = row.to_dict()
    
    # Append the dictionary to the list
    data_list.append(row_data)

# Construct the output JSON file path
json_file_path = excel_file_path.replace('.xlsx', '.json')

# Write the data to a JSON file
with open(json_file_path, 'w') as json_file:
    json.dump(data_list, json_file, indent=4)


print(f"Python Function list JSON file has been generated at {json_file_path}")
