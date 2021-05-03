#!/usr/bin/env python3

import os
import io
import datetime
import shutil
from PIL import Image
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import argparse
import mimetypes
import exifread
from collections import Counter
from enum import Enum

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class ParseType(Enum):   
    EXIFREAD = "exifread"
    PILLOW = "Pillow"
    HACHOIR = "hachoir"
    FILEDATE = "File date"
    ERROR = "No date found"

def get_formatted_date(date):
    if date is not None:
        return date.strftime("%Y_%m_%d_%H_%M_%S")
    else:
        return "ERR_DATE"

class FileProperties:
    def __init__(self, original_path):
        self.src_file = original_path
        self.dst_file = original_path
        self.root_path = os.getcwd()    

        self.size = os.path.getsize(self.src_file)

        self.date_taken = None
        self.date_found_method = ParseType.ERROR
        self.file_type = mimetypes.guess_type(self.src_file)[0]
        self.is_duplicate = False
        self.is_valid = False
        self.date_append = ""

    def get_src_file_name(self):
        return self.src_file.replace(self.root_path, "")

    def get_dst_file_name(self):
        return self.dst_file.replace(self.root_path, "")

    def set_duplicate_count(self, count):
        self.date_append = "_" + str(count)
        self.set_date_as_file_name()

    def set_date_taken(self, date):
        self.date_taken = get_formatted_date(date)
        self.set_date_as_file_name()

    def set_date_as_file_name(self):
        file_name, ext = os.path.splitext(os.path.basename(self.src_file))
        formatted_file_name = self.date_taken + self.date_append + ext
        self.dst_file = os.path.join(os.path.dirname(self.dst_file), formatted_file_name)

    def replace_root_path(self, new_path):
        self.dst_file = self.src_file.replace(self.root_path, new_path)

    def copy(self):
        dirname = os.path.dirname(self.dst_file)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        shutil.copy(self.src_file, self.dst_file)

    def __eq__(self, other):
        if type(other) is type(self):
            return self.date_taken == other.date_taken
        return False
    
    def __hash__(self):
        return hash(self.date_taken)

def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

def get_files_in_dir(dir):
    file_list = list()
    for path, subdirs, files in os.walk(dir):
        for name in files:
            file_list.append(FileProperties(os.path.join(path, name)))
    return file_list

def get_value_in_nested_dict(d, key):
    for k, v in d.items():
        if isinstance(v, dict):
            if key in v:
                return v[key]
            else:
                get_value_in_nested_dict(v, key)
        if key in v:
            return v[key]
    return None

def check_valid_date(date):
    if date > valid_date_limit:
        return date
    else:
        return None

def get_file_modified_date(file_prop):
        timestamp = os.path.getmtime(file_prop.src_file)
        date = datetime.datetime.fromtimestamp(timestamp)
        return check_valid_date(date)

def parse_date(date, format = "%Y:%m:%d %H:%M:%S"):
    date_obj = None
    try:
        date_obj = datetime.datetime.strptime(str(date), format)
    except:
        return None
    else: 
        return check_valid_date(date_obj)

def parse_video(file_prop):
    parser = createParser(file_prop.src_file)
    if not parser:
        print("Unable to parse file %s" % file_prop.src_file)
        return None
    with parser:
        try:
            metadata = extractMetadata(parser)
        except Exception as err:
            print("Metadata extraction error: %s" % err)
            metadata = None
    if not metadata:
        print("Unable to extract metadata")
        return None
    meta = metadata.exportDictionary()
    date = get_value_in_nested_dict(meta, "Creation date")
    if date is not None:
        return parse_date(date, format="%Y-%m-%d %H:%M:%S")
    return None

def parse_image(file_prop):
    f = open(file_prop.src_file, 'rb')
    dates = list()
    dates.append(None)
    tags = exifread.process_file(f, stop_tag="DateTimeOriginal", details=False)
    field = "EXIF DateTimeOriginal"

    if field in tags:
        dates.append(parse_date(tags[field]))

    if dates[-1] is None:
        exif = Image.open(f).getexif()
        tags = [36867, 306]
        for tag in tags:
            if tag in exif:
                dates.append(parse_date(exif[tag]))
    
    dates_sorted = sorted(dates, key=lambda x: (x is None, x))
    f.close()
    return dates_sorted[0]

def get_date_taken(file_prop):
    date = None
    if file_prop.file_type is not None:
        if "image" in file_prop.file_type:
            date = parse_image(file_prop)
        else:
            date = parse_video(file_prop)

    if date is None and date_mod_check:
        date = get_file_modified_date(file_prop)
    
    return date

def print_to_string(*args, **kwargs):
    output = io.StringIO()
    print(*args, file=output, **kwargs)
    contents = output.getvalue()
    output.close()
    return contents

def find_and_remove_duplicates(file_props):
    d =  Counter(file_props) 
    res = [k for k, v in d.items() if v > 1]
    dups = dict()
    for fp_dup in res:
        dups[fp_dup.date_taken] = [fp_dup]
        for fp in file_props:
            if fp_dup == fp and fp_dup.src_file != fp.src_file:
                dups[fp_dup.date_taken].append(fp)

    output_str = str()
    output_str += print_to_string("Found {} duplicate files!".format(len(dups)))
    for key, fp_list in dups.items():
        fp_list = sorted(fp_list, key=lambda x:x.size, reverse=True)
        output_str += print_to_string("Duplicates: ", end="")
        for fp in fp_list:
            output_str += print_to_string("{: <40}".format(fp.get_src_file_name()), end='')
        output_str += print_to_string()

    for key, fp_list in dups.items():
        for c, fp in enumerate(fp_list[1:]):
            base_filename, base_ext = os.path.splitext(fp_list[0].src_file)
            count = c + 1
            #print(count)
            for i, fpv in enumerate(file_props):
                if fp == fpv:
                    if fp.src_file == fpv.src_file:
                        fp.set_duplicate_count(count)
                        count += 1
                        if not ignore_dup:
                            del file_props[i]
    if ignore_dup:
        return "Found 0 duplicate files!\n"
    else:
        return output_str

def copy_files(file_prop_list):
    if len(file_prop_list) > 0:
        printProgressBar(0, len(file_prop_list), prefix = 'Copying:', suffix = 'Complete', length = 50)
        for i, fp in enumerate(file_prop_list):
            fp.copy()
            printProgressBar(i + 1, len(file_prop_list), prefix = 'Copying:', suffix = 'Complete', length = 50)

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-cp", action='store_true')
    parser.add_argument("-dm", action='store_true')
    parser.add_argument("-id", action='store_true')
    args = parser.parse_args()

    root = os.getcwd()
    valid_dest = root + "_mod"
    invalid_dest = root + "_error"

    do_copy = args.cp
    date_mod_check = args.dm
    ignore_dup = args.id

    valid_date_limit = datetime.datetime.strptime("2001:01:01 00:00:00", "%Y:%m:%d %H:%M:%S")

    valid_file_props = list()
    invalid_file_props = list()
    file_list = get_files_in_dir(root)
    
    printProgressBar(0, len(file_list), prefix = 'Searching:', suffix = 'Complete', length = 50)
    for i, file in enumerate(file_list):
        date_taken = get_date_taken(file)
        if date_taken is None:
            file.replace_root_path(invalid_dest)
            invalid_file_props.append(file)
        else:
            file.replace_root_path(valid_dest)
            file.set_date_taken(date_taken)
            valid_file_props.append(file)
        printProgressBar(i + 1, len(file_list), prefix = 'Searching:', suffix = 'Complete', length = 50)

    output_str = find_and_remove_duplicates(valid_file_props)

    print(bcolors.OKGREEN, "Found {} good files!".format(len(valid_file_props)), bcolors.ENDC)
    for fp in valid_file_props:
        print(bcolors.OKGREEN, "{: <60} ---> {}".format(fp.get_src_file_name(), fp.get_dst_file_name()), bcolors.ENDC)

    print(bcolors.WARNING, output_str, bcolors.ENDC, end='')

    print(bcolors.FAIL, "Found {} bad files!".format(len(invalid_file_props)), bcolors.ENDC)
    for fp in invalid_file_props:
        formatted_date = get_formatted_date(get_file_modified_date(fp))
        print(bcolors.FAIL, "{: <60} ---> {}".format(fp.get_src_file_name(), formatted_date), bcolors.ENDC)

    if do_copy:
        copy_files(valid_file_props)
        copy_files(invalid_file_props)