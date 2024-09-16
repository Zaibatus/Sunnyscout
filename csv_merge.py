import pandas as pd

# Load the original CSV
original_csv = pd.read_csv('cities_airports_old.csv')

# Load the new data (the exported Google Sheets CSV)
new_data = pd.read_csv('costs.csv')

# Merge the data
# If the 'City' column is the common identifier, merge on 'City'
merged_data = pd.merge(original_csv, new_data, on='City', how='left')

# Fill NaN values in the new columns with appropriate defaults if needed
merged_data['Cost_Scale'].fillna('Unknown', inplace=True)
merged_data['Euro'].fillna('Unknown', inplace=True)

# Save the merged data back to a CSV file
merged_data.to_csv('cities_airports.csv', index=False)

print("CSV updated successfully.")
