import subprocess
from typing import Callable, List, Optional, Tuple
import requests
import bs4
from pathlib import Path
import shutil
from queue import Queue
from threading import Thread
import re
import time
import random
import zipfile
import os

CLEANUP_ENABLED = False
NUM_RETRIES = 5
NUM_THREADS = 8

MAIN_QUEUE: 'Queue[Tuple[str, int]]' = Queue(maxsize=0)


def create_cbz(chapter_folder: Path):
    """ Creates a cbz file from the folder

    Args:
        chapter_folder (Path): The folder to zip and change to cbz
    """

    cbz_file_name = chapter_folder.name + '.cbz'
    out_path = chapter_folder.parent.joinpath(cbz_file_name)
    # Zip the folder
    try:

        with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zip:
            for root, dirs, files in os.walk(chapter_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    zip.write(file_path, os.path.relpath(file_path, chapter_folder))


    except Exception as e:
        print(f'ERROR: Couldn\'t zip folder: {chapter_folder.name}', e)


def _download_image_in_folder(url: str, folder_path: Path, index: int, try_count: int = 0):
    """Download the image into the folder

    _extended_summary_

    Args:
        url (str): Url of the image
        folder_path (Path): Path of the folder to download the image into
        index (int): Index of the image
        try_count (int, optional): Max number of download retries. Defaults to 0.
    """
    # Get the extension
    extension = url.split('.')[-1]
    # get File name from url
    file_path = folder_path.joinpath(f'{index:0004d}.{extension}')
    
    print(file_path.absolute())
    # Download the image
    try:
        # res = requests.get(url, stream = True, timeout=2)
        # wget -O file_path url in shell
        process = subprocess.Popen(['wget', '-O', str(file_path.absolute()), url])
        # wait for subprocess to finish
        process.wait()
    except:
        print(f'ERROR: Image Couldn\'t be retrieved: {url}')
        # Retry 5 times with a random delay
        if try_count < NUM_RETRIES:
            try_count += 1
            print(f'Retrying download {try_count+1}/5')
            time.sleep(random.randint(1, 10))
            _download_image_in_folder(url, folder_path, index, try_count)
        return


def _find_all_images(url: str) -> List[str]:
    """Find all the images in the page returned in the url

    This is intentionally left black so that the user can implement their own image finder.

    This function exists to establish a common interface for all the image finders and 
    throw an error if the user doesn't implement it.

    Args:
        url (str): The url to find the images in

    Raises:
        NotImplementedError: This function is not implemented yet, please implement it in your code

    Returns:
        List[str]: A list of all the image urls
    """
    raise NotImplementedError('This function is not implemented yet')


def download_chapter(
    que: Queue, 
    find_all_images: Callable[[str], List[str]]=_find_all_images, 
    series_name: str = 'unnamed-series',
    chapter_number_regex_pattern: Optional[str] = None,
):
    """Download the chapter from the url

    This function is the primary consumer of the queue. It takes the url from the queue and downloads the chapter.
    
    Naming info example:
    naming_info=('Tensei-shitara-Slime-Datta-Kenei', r'\d+-\d+')

    Args:
        que (Queue): The queue to get the url from
        find_all_images (Callable[[str], List[str]], optional): Function ref that will find the images. Defaults to _find_all_images.
        series_name (str, optional): The name of the series. Defaults to 'unnamed-series'.
        chapter_number_regex_pattern (Optional[str], optional): The regex pattern for finding the chapter number in the url. Defaults to None.
    """
    while que.empty() is False:
        # Get the url from the queue
        url, chapter_number = que.get()
        # Go through each url and download the html
        # Get the HTML from the page
        chapter_name = url.split('/')[-1]
        print(f'Searching URL: {url}')
        image_urls = find_all_images(url)
        print(f'Found {len(image_urls)} images')

        # Extract the chapter number from the chapter_name and replace it with a padded number
        # if no chapter number is found
        if chapter_number is None:
            match = re.search(r'\d+', chapter_name)
            if match:
                chapter_number = match.group(0)
                padded_number = f'{int(chapter_number):05d}'
                chapter_name = f'{series_name}-{padded_number}'
        
        elif chapter_number_regex_pattern is not None:
            match = re.search(chapter_number_regex_pattern, chapter_name)
            if match:
                chapter_number = match.group(0)
                padded_number = f'{int(chapter_number):05d}'
                chapter_name = f'{series_name}-{padded_number}'

        else:
            # If chapter number is provided, replace the chapter number in the chapter name
            padded_number = f'{int(chapter_number):05d}'
            chapter_name = f'{series_name}-{padded_number}'
        
        print(f'Chapter Name: {chapter_name}')    # Create a new folder for the chapter using pathlib
        chapter_folder = Path("./").parent.joinpath(chapter_name)
        
        # Create the folder if it doesn't exist
        chapter_folder.mkdir(exist_ok=True)

        # Download each image into the folder
        for index, image_url in enumerate(image_urls):
            print(f'Downloading image: {index} : {image_url}')
            # Download the image using wget
            print(chapter_folder.absolute())
            _download_image_in_folder(image_url, chapter_folder, index)
        
        create_cbz(chapter_folder)

        # Delete the folder
        if CLEANUP_ENABLED:
            try:
                shutil.rmtree(chapter_folder.resolve())
            except:
                print(f'ERROR: Couldn\'t delete folder: {chapter_folder.resolve()}')
    
        print(f'Finished downloading chapter: {chapter_name}')
        # Mark the task as done
        print(f'Marking task as done: {url}')
        que.task_done()

    
def cleanup_url(url: str) -> str:
    """ Helper function to cleanup the url

    CASES:
    1. Remove the last slash from the url
    2. TBA in the future

    Args:
        url (str): The url to cleanup

    Returns:
        str: The cleaned up url
    """
    # Case 1 - Remove the last slash from the url
    if url[-1] == '/':
        url = url[:-1]
    return url


def start_download(
    chapter_urls_file: Path,
    image_finder_callback: Callable[[str], List[str]], 
    series_name: str, 
    chapter_number_regex: Optional[str], 
    reverse_url_order: bool = False,
    overwrite_chapter_numbers: bool = False
):
    """Start the download of the chapters

    This is the starting point for the downloader. It reads the urls from the file and puts them in the queue.

    Args:
        chapter_urls_file (Path): The path to the file containing the urls
        image_finder_callback (Callable[[str], List[str]]): The function that will find the images in the url
        series_name (str): The name of the series
        chapter_number_regex (Optional[str]): The regex pattern for finding the chapter number in the url. If none, it doesn't try to find the chapter number
        reverse_url_order (bool, optional): If the urls needs to downloaded in the reverse order in the text file. Defaults to False.
        overwrite_chapter_numbers (bool, optional): If the chapter numbers in the url needs to be overwritten with the chapter numbers in the text file. Defaults to False.
    """
    
    # Read the urls from the file `chapterlisturls.txt`
    with open(chapter_urls_file.absolute(), 'r') as f:
        chapter_urls = f.read().splitlines()
    
    # Reverse the urls
    if reverse_url_order:
        chapter_urls.reverse()

    chapter_number_index = 1
    for url in chapter_urls:
        # Skip if empty url
        if url == "":
            continue
        # Cleanup the url
        url = cleanup_url(url)
        # Put the pdf link in the queue
        MAIN_QUEUE.put((url, chapter_number_index))
        chapter_number_index += 1
    
    #split the urls into chunks of Threads
    for i in range(NUM_THREADS):
        worker = Thread(target=download_chapter, args=(MAIN_QUEUE, image_finder_callback, series_name, chapter_number_regex))
        worker.setDaemon(True)
        worker.start()

    # Wait until the queue has been processed
    print('Waiting for queue to be processed')
    MAIN_QUEUE.join()


def extract_names_from_ziplist(zip_list:List[str], chapter_number_regex_pattern:str= r'^(.*?)-\d+') -> Tuple[str, int, int]:
    """Extract the names from the zip files list and return the series name, min chapter number and max chapter number

    Args:
        zip_list (List[str]): List of zipfiles
        chapter_number_regex_pattern (str, optional): regex for finding the chapter number from the zipfile name. Defaults to r'^(.*?)-\d+'.

    Returns:
        Tuple[str, int, int]: Tuple containing the series name, min chapter number and max chapter number
    """
    # Extract the chapter number from the zip file names and get highest and lowest chapter numbers
    results = map(lambda file_name: int(re.search(r'\d+', file_name).group(0)), zip_list)
    chapter_numbers = list(results)
    min_chapter = min(chapter_numbers)
    max_chapter = max(chapter_numbers)

    file_name = zip_list[0]
    match = re.search(chapter_number_regex_pattern, file_name)
    series_name = 'unnamed-series'
    if match:
        series_name = match.group(1)
    
    print(f"Min Chapter: {min_chapter}, Max Chapter: {max_chapter}, Series Name: {series_name}")
    return series_name, min_chapter, max_chapter


def merge_zip_files(input_folder: Path, output_folder: Path = Path("./volumes"), batch_size: int = 10):
    """Merge the zip files in the input folder into a single zip file

    Args:
        input_folder (Path): The folder containing the zip files
        output_folder (Path, optional): The folder where the output should go . Defaults to Path("./volumes").
        batch_size (int, optional): number of items to merge. Defaults to 10.
    """
    zip_files = [f for f in os.listdir(str(input_folder.absolute())) if f.endswith('.cbz') or f.endswith('.cbr')]
    print(zip_files)
    zip_files.sort()
    print(zip_files)
    for i in range(0, len(zip_files), batch_size):
        batch = zip_files[i:i+batch_size]
        series_name, min_chapter, max_chapter = extract_names_from_ziplist(batch)
        batch_output_folder = output_folder.joinpath((f'{series_name}-{min_chapter:005d}-{max_chapter:005d}'))
        batch_output_folder.mkdir(exist_ok=True, parents=True)

        index = 1
        for f in batch:
            input_zip = input_folder.joinpath(f)
            print(f'Extracting {input_zip} ...')
            with zipfile.ZipFile(input_zip, 'r') as input_zf:
                # Go through each file in the zip file
                memberlist = input_zf.namelist()

                # Skip if empty zip file
                if len(memberlist) == 0:
                    print(f'ERROR: {input_zip} is empty')
                    continue
                
                extension = memberlist[0].split('.')[-1]
                memberlist.sort()
                print(memberlist)
                for file in memberlist:
                    input_zf.extract(file, batch_output_folder)
                    # rename the file to 
                    os.rename(os.path.join(batch_output_folder, file), os.path.join(batch_output_folder, f'{index:0005d}.{extension}'))
                    print(f'Renamed {file} to {index:0005d}.{extension}')
                    index += 1
                    
        create_cbz(batch_output_folder)

        # Delete the folder
        if CLEANUP_ENABLED:
            shutil.rmtree(batch_output_folder)
