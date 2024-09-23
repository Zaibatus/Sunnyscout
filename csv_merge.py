import pandas as pd

# Load the original CSV
original_csv = pd.read_csv('cities_airports.csv')

# Load the new data (the carousel image CSV)
new_data = pd.read_csv('carousel_images.csv')

# Merge the data
# Assuming 'City' is the common identifier in both CSVs
merged_data = pd.merge(original_csv, new_data[['City', 'city_img_0']], on='City', how='left')

# Fill NaN values in the new columns with appropriate defaults if needed
merged_data['city_img_0'].fillna('https://example.com/default-image.jpg', inplace=True)

# Save the merged data back to a CSV file
merged_data.to_csv('cities_airports.csv', index=False)

print("CSV updated successfully with carousel images.")
