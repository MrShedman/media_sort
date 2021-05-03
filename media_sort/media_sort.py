#!/usr/bin/env python3

import os
import io
import datetime
import shutil
import filetype
from os import listdir
from os.path import isfile, join
from PIL import Image
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import argparse
import mimetypes
import exifread
from collections import Counter

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

class FileProperties:
    def __init(self):
        self.original_path = ""
        self.modified_path = ""
        self.date_str = ""
        self.file_size = ""
        self.file_name = ""
        self.src_file = ""
        self.dest_file = ""

    def __eq__(self, other):
        if type(other) is type(self):
            return self.date_str == other.date_str
        return False
    
    def __hash__(self):
        #print(hash(str(self)))
        return hash(self.date_str)

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
            file_list.append(os.path.join(path, name))
    return file_list

def get_pretty_name(date_taken):
    date_taken_str = str(date_taken)
    bad_chars = ":- "
    for i in bad_chars:
        date_taken_str = date_taken_str.replace(i, '_')
    return date_taken_str

def check_valid_date(date):
    if date > valid_date_limit:
        return date
    else:
        return None

def get_file_modified_time(filename):
    timestamp = os.path.getmtime(filename)
    date = datetime.datetime.fromtimestamp(timestamp)
    return check_valid_date(date)

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

def parse_date(date, format = "%Y:%m:%d %H:%M:%S"):
    date_obj = None
    try:
        date_obj = datetime.datetime.strptime(str(date), format)
    except:
        return None
    else: 
        return check_valid_date(date_obj)

def parse_video(filename):
    parser = createParser(filename)
    if not parser:
        print("Unable to parse file %s" % filename)
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

def parse_image(filename):
    f = open(filename, 'rb')
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

def get_date_taken(path):
    file_type = mimetypes.guess_type(path)[0]
    date = None
    if file_type is not None:
        if "image" in file_type:
            date = parse_image(path)
        else:
            date = parse_video(path)

    if date is None and date_mod_check:
        date = get_file_modified_time(path)
    
    return date

def get_dest_dir(file, dest_path):
    if copy_files:
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
    dirname = os.path.dirname(file)
    filename, ext = os.path.splitext(os.path.basename(file))
    dest_dir = dirname.replace(root, dest_path)
    if copy_files:
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

    return dest_dir, filename, ext

def handle_invalid(file):
    dest_dir, filename, ext = get_dest_dir(file, invalid_dest)
    dest_file = os.path.join(dest_dir, os.path.basename(filename) + ext)
    if copy_files:
        shutil.copy(file, dest_file)
    invalid_file_names.append(file)

def handle_valid(file):
    dest_dir, filename, ext = get_dest_dir(file, valid_dest)
    dest_file = os.path.join(dest_dir, get_pretty_name(data_taken) + ext)

    file_prop = FileProperties()
    file_prop.original_path = file.replace(root, "")
    file_prop.modified_path = dest_file.replace(valid_dest, "")
    file_prop.file_name = os.path.basename(file_prop.modified_path)
    file_prop.date_str = get_pretty_name(data_taken)
    file_prop.file_size = os.path.getsize(file)
    file_prop.dest_file = dest_file
    file_prop.src_file = file

    valid_file_props.append(file_prop)
    valid_file_names.append(file)

def add_seconds_to_date(date_str, seconds):
    date_new = date_str + "_" + str(seconds)
    return date_new

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
        dups[fp_dup.date_str] = [fp_dup]
        for fp in file_props:
            if fp_dup == fp and fp_dup.original_path != fp.original_path:
                dups[fp_dup.date_str].append(fp)

    output_str = str()
    output_str += print_to_string("Found {} duplicate files!".format(len(dups)))
    for key, fp_list in dups.items():
        fp_list = sorted(fp_list, key=lambda x:x.file_size, reverse=True)
        output_str += print_to_string("Duplicates: ", end="")
        for fp in fp_list:
            output_str += print_to_string("{: <40}".format(fp.original_path), end='')
        output_str += print_to_string()

    for key, fp_list in dups.items():
        for c, fp in enumerate(fp_list[1:]):
            base_filename, base_ext = os.path.splitext(fp_list[0].file_name)
            count = c + 1
            #print(count)
            for i, fpv in enumerate(file_props):
                if fp == fpv:
                    if fp.original_path == fpv.original_path:
                        dirname = os.path.dirname(fp.dest_file)
                        filename, ext = os.path.splitext(os.path.basename(fp.dest_file))
                        filename_mod = add_seconds_to_date(filename, count)
                        count += 1
                        new_file = os.path.join(dirname, filename_mod + ext)
                        #print(new_file)
                        fp.dest_file = new_file
                        fp.modified_path = new_file.replace(valid_dest, "")
                        if not ignore_dup:
                            del file_props[i]
    if ignore_dup:
        return "Found 0 duplicate files!\n"
    else:
        return output_str

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-cp", action='store_true')
    parser.add_argument("-dm", action='store_true')
    parser.add_argument("-id", action='store_true')
    args = parser.parse_args()

    root = os.getcwd()
    valid_dest = root + "_mod"
    invalid_dest = root + "_error"

    copy_files = args.cp
    date_mod_check = args.dm
    ignore_dup = args.id

    valid_date_limit = datetime.datetime.strptime("2001:01:01 00:00:00", "%Y:%m:%d %H:%M:%S")

    invalid_file_names = list()
    valid_file_names = list()
    valid_file_props = list()
    file_list = get_files_in_dir(root)
    
    printProgressBar(0, len(file_list), prefix = 'Searching:', suffix = 'Complete', length = 50)
    for i, file in enumerate(file_list):
        data_taken = get_date_taken(file)
        if data_taken is None:
            handle_invalid(file)
        else:
            handle_valid(file)
        printProgressBar(i + 1, len(file_list), prefix = 'Searching:', suffix = 'Complete', length = 50)

    output_str = find_and_remove_duplicates(valid_file_props)

    print(bcolors.OKGREEN, "Found {} good files!".format(len(valid_file_names)), bcolors.ENDC)
    for fp in valid_file_props:
        print(bcolors.OKGREEN, "{: <60} ---> {}".format(fp.original_path, fp.modified_path), bcolors.ENDC)

    print(bcolors.WARNING, output_str, bcolors.ENDC, end='')

    print(bcolors.FAIL, "Found {} bad files!".format(len(invalid_file_names)), bcolors.ENDC)
    for file in invalid_file_names:
        print(bcolors.FAIL, file, bcolors.ENDC)

    if copy_files:
        printProgressBar(0, len(valid_file_props), prefix = 'Copying:', suffix = 'Complete', length = 50)
        for i, fp in enumerate(valid_file_props):
            shutil.copy(fp.src_file, fp.dest_file)
            printProgressBar(i + 1, len(valid_file_props), prefix = 'Copying:', suffix = 'Complete', length = 50)
