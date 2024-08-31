import os
import requests
from urllib.parse import urlparse

# Create the main folder
main_folder = "fasthtml_docs"
os.makedirs(main_folder, exist_ok=True)

# Read URLs from the file
with open('fasthtmldocs_urls.txt', 'r') as f:
    urls = f.read().splitlines()

for url in urls:
    # Parse the URL to get the path
    parsed_url = urlparse(url)
    path = parsed_url.path.lstrip('/')

    # Create subfolders if needed
    folders = os.path.dirname(path)
    if folders:
        os.makedirs(os.path.join(main_folder, folders), exist_ok=True)

    # Download the content
    response = requests.get(url)
    if response.status_code == 200:
        # Save the content to a file
        file_path = os.path.join(main_folder, path)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded: {file_path}")
    else:
        print(f"Failed to download: {url}")

print("Download complete.")
