import os
import sys
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


def download_images_from_jike(url):
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # 选择两种形式的 div 元素
        div_elements = soup.select('div.jsx-1271604522.wrap, div.jsx-1271604522.wrap.single')

        title1 = soup.find('div', class_="jsx-3802438259 title")
        title2 = soup.find('div', class_="jsx-3930310120 wrap")

        if div_elements and title1 and title2:
            title = f"{title1.text.strip()}_{title2.text.strip()}"
            total_images = 0

            # 遍历所有符合条件的 div 元素
            for div_element in div_elements:
                img_elements = div_element.find_all('img')
                total_images += len(img_elements)

                # 创建文件夹
                folder_path = os.path.join(title)
                os.makedirs(folder_path, exist_ok=True)

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
    if len(sys.argv) != 2:
        print("Usage: python script.py <jike_url>")
        sys.exit(1)

    jike_url = sys.argv[1]
    download_images_from_jike(jike_url)
