from pathlib import Path
from typing import List
from cbz_maker import start_download, merge_zip_files
import requests
import bs4


def find_image_urls(url) -> List[str]:
    res = requests.get(url)
    soup = bs4.BeautifulSoup(res.text, 'html.parser')

    # Find all image elements
    images = soup.find_all('img')
    image_metas = [image for image in images if image["class"]]

    # Select the images with the alt that start with "Tensei shitara Slime Datta Ken"
    images = [image for image in image_metas if 'size-full' in image['class']]
    # Extract the image urls
    image_urls = [image['src'] for image in images if 'svg' not in image['src']]
    return image_urls


start_download(
    chapter_urls_file=Path('/Users/krishna/scraper-projects/demon-slayer/leftovers.txt'),
    image_finder_callback=find_image_urls,
    naming_info=('Demon-Slayer', r'\d+'),
    reverse_url_order=True
)

merge_zip_files(
    input_folder=Path("/Users/krishna/scraper-projects/demon-slayer"),
    output_folder=Path("./volumes"), 
    batch_size=10
)
