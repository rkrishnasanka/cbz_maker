import os
import re



def file_volume_file_names(folder_path:str):

    pattern = re.compile(r'(\d+)-(\d+)')

    for file_name in os.listdir(folder_path):
        print(file_name)
        replacement = {"1":"001","2":"002"}

        match = re.finditer(pattern, file_name)
        for index, m in enumerate(match):
            print(index)

            chapter_number_min = int(m.group(1))
            padded_number_min = f'{chapter_number_min:0005d}'

            chapter_number_max = int(m.group(2))
            padded_number_max = f'{chapter_number_max:0005d}'

            print(padded_number_min, padded_number_max)
            replacement = {"1":padded_number_min,"2":padded_number_max}

        new_file_name = re.sub(r'\d+-\d+', f'{replacement["1"]}-{replacement["2"]}', file_name)
        old_path = os.path.join(folder_path, file_name)
        new_path = os.path.join(folder_path, new_file_name)
        os.rename(old_path, new_path)

