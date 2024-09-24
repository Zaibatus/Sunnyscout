import csv
from googleapiclient.discovery import build


def search_city_images(city_name, api_key, cse_id, num_images=4):
    service = build("customsearch", "v1", developerKey=api_key)

    # Perform the search for high-quality images while excluding images with logos or signs
    result = service.cse().list(
        q=f"{city_name} google",  # Exclude images with text like logos or signs
        cx=cse_id,
        searchType="image",
        num=num_images,  # Request 4 images for the city
        imgType="photo",
        imgSize="XLARGE",
        siteSearch="Google.com",
        siteSearchFilter="i",
        safe="active",
        fileType="jpg,png",
        filter="1",
    ).execute()

    # Extract image URLs from the result
    images = []
    for item in result.get('items', []):
        images.append(item['link'])

    return images


def update_csv_with_images(csv_file, api_key, cse_id, max_api_calls=98):
    api_calls_made = 0

    # Read the existing CSV data
    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        cities_data = list(reader)

    # Add image URLs for each city
    for city in cities_data:
        if api_calls_made >= max_api_calls:
            print("API call limit reached. Stopping further requests.")
            break

        city_name = city['City']

        # Check if all city_img fields are already filled
        if all(city.get(f'city_img_{i}') for i in range(1, 5)):
            print(f"Skipping {city_name}: All image fields are already filled.")
            continue

        print(f"Searching images for: {city_name}")

        # Search for 4 high-quality images for the city
        image_urls = search_city_images(city_name, api_key, cse_id, num_images=4)

        # Increment API call count (each city search counts as 1 API call)
        api_calls_made += 1

        # Update the city row with image URLs (ensure we have up to 4 images)
        for i in range(4):
            column_name = f"city_img_{i + 1}"
            if not city.get(column_name):  # Only update if the field is empty
                city[column_name] = image_urls[i] if i < len(image_urls) else "No image found"

    # Write the updated data back to the CSV
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        fieldnames = ['City', 'city_img_1', 'city_img_2', 'city_img_3', 'city_img_4']
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Write the header and updated rows
        writer.writeheader()
        writer.writerows(cities_data)


api_key = 'AIzaSyAdmtoHZtAWUz3ututJDGxQ5p9sRvK3G8U'
cse_id = 'f419c64b875494a64'
csv_file = 'carousel_images_cities_3.csv'

# Call the function with a limit of 98 API calls
update_csv_with_images(csv_file, api_key, cse_id, max_api_calls=98)
