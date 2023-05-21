from pathlib import Path
from typing import List
from cbz_maker import start_download, merge_zip_files
import requests
import bs4



def find_image_urls(url) -> List[str]:
    res = requests.get(url)
    soup = bs4.BeautifulSoup(res.text, 'html.parser')

    # Find all image elements
    images = soup.find_all('meta', {'property':'og:image'})
    # # Select the images with the alt that start with "Tensei shitara Slime Datta Ken"
    # images = [image for image in images if image['alt'].startswith('Tensei')]
    # Extract the image urls
    image_urls = [image['content'] for image in images]
    return image_urls


start_download(
    chapter_urls_file=Path('chapterurls.txt'),
    image_finder_callback=find_image_urls,
    # naming_info=('Tensei-shitara-Slime-Datta-Kenei', r'\d+-\d+'),
    series_name='Tensei-shitara-Slime-Datta-Kenei',
    chapter_number_regex=None,
    overwrite_chapter_numbers=True,
)

merge_zip_files(
    input_folder=Path("./"),
    output_folder=Path("./"),
    batch_size=10
)
