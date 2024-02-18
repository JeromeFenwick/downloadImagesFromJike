import os
import sys
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


def download_images_from_jike(url):
    # Send a GET request to the specified URL
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Select div elements with specific classes
        div_elements = soup.select('div.jsx-1271604522.wrap, div.jsx-1271604522.wrap.single')

        # Find title elements
        title1 = soup.find('div', class_="jsx-3802438259 title")
        title2 = soup.find('div', class_="jsx-3930310120 wrap")

        # Check if all required elements are found
        if div_elements and title1 and title2:
            # Combine titles to create a folder name
            title = f"{title1.text.strip()}_{title2.text.strip()}"
            total_images = 0

            # Iterate over all selected div elements
            for div_element in div_elements:
                # Find all image elements within the div
                img_elements = div_element.find_all('img')
                total_images += len(img_elements)

                # Create a folder for images
                folder_path = os.path.join(title)
                os.makedirs(folder_path, exist_ok=True)

                # Download and save each image
                for idx, img in tqdm(enumerate(img_elements, start=1), total=len(img_elements),
                                     desc=f"Downloading images for {title}"):
                    src = img.get('src')

                    # Download image
                    img_response = requests.get(src)

                    # Check if the request was successful
                    if img_response.status_code == 200:
                        # Save the image to the specified folder
                        img_name = f"image_{idx}.jpg"
                        img_path = os.path.join(folder_path, img_name)

                        with open(img_path, 'wb') as img_file:
                            img_file.write(img_response.content)
                    else:
                        print(f"Failed to download image {idx}/{total_images}. Status code: {img_response.status_code}")

            print(f"\nAll images for {title} downloaded.")
        else:
            print("Div or title elements not found on the page.")
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")


if __name__ == "__main__":
    # Check if the correct number of command-line arguments is provided
    if len(sys.argv) != 2:
        print("Usage: python script.py <jike_url>")
        sys.exit(1)

    # Extract Jike URL from command-line arguments
    jike_url = sys.argv[1]

    # Call the main function to download images
    download_images_from_jike(jike_url)
