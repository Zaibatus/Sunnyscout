import pandas as pd

# Load the original CSV
original_csv = pd.read_csv('cities_airports.csv')

# Load the new data (the carousel image CSV)
new_data = pd.read_csv('carousel_images_cities.csv')

# Merge the data
# Assuming 'City' is the common identifier in both CSVs
merged_data = pd.merge(original_csv, new_data, on='City', how='left')

# Fill NaN values in the new columns with appropriate defaults if needed
# Adjust column names as necessary
merged_data['city_img_1'].fillna('https://example.com/default-image.jpg', inplace=True)
merged_data['city_img_2'].fillna('https://example.com/default-image.jpg', inplace=True)
merged_data['city_img_3'].fillna('https://example.com/default-image.jpg', inplace=True)
merged_data['city_img_4'].fillna('https://example.com/default-image.jpg', inplace=True)


# Save the merged data back to a CSV file
merged_data.to_csv('cities_airports.csv', index=False)

print("CSV updated successfully with carousel images.")
