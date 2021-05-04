#!/usr/bin/env python3

import os
import datetime
import shutil
import argparse
import mimetypes

from media_sort.parsers import FileModifiedParser, PillowParser, ExifReadParser, HachoirParser, ParseType
from media_sort.utils import print_progress_bar, print_to_string, TermColors

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
        self.parse_method = ParseType.ERROR
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

def get_files_in_dir(dir):
    file_list = list()
    for path, subdirs, files in os.walk(dir):
        for name in files:
            file_list.append(FileProperties(os.path.join(path, name)))
    return file_list

def parse_video(file_prop):
    hachoir = HachoirParser(file_prop.src_file)
    return hachoir.get_result()

def parse_image(file_prop):
    exifread = ExifReadParser(file_prop.src_file)
    date, parse_type = exifread.get_result()
    if date is None:
        pillow = PillowParser(file_prop.src_file)
        date, parse_type = pillow.get_result()
    
    return date, parse_type

def get_date_taken(file_prop):
    date = None
    parse_type = ParseType.ERROR
    if file_prop.file_type is not None:
        if "image" in file_prop.file_type:
            date, parse_type = parse_image(file_prop)
        else:
            date, parse_type = parse_video(file_prop)

    if date is None and date_mod_check:
        fmod = FileModifiedParser(file_prop.src_file)
        date, parse_type = fmod.get_result()
    
    return date, parse_type

def find_and_remove_duplicates(file_props):
    dict_fp = dict()

    for i, fp in enumerate(file_props):
        if fp in dict_fp:
            dict_fp[fp].append((fp, i))
        else:
            dict_fp[fp] = [(fp, i)]

    indices_to_remove = list()
    output_str = str()
    for key, fp_list in dict_fp.items():
        if len(fp_list) > 1:
            output_str += print_to_string("Found {} duplicate files!".format(len(fp_list)))
            fp_list = sorted(fp_list, key=lambda x:x[0].size, reverse=True)
            for i, (fp, oc) in enumerate(fp_list[1:]):
                fp.set_duplicate_count(i+1)
                indices_to_remove.append(oc)
            for fp, oc in fp_list:
                output_str += print_to_string("\t{:<80}{}".format(fp.get_src_file_name(), fp.file_type))
            output_str += print_to_string()

    if not ignore_dup:
        file_props[:] = [fp for i, fp in enumerate(file_props) if i not in indices_to_remove]

    if ignore_dup:
        return "Found 0 duplicate files!\n"
    else:
        return output_str

def copy_files(file_prop_list):
    if len(file_prop_list) > 0:
        print_progress_bar(0, len(file_prop_list), prefix = 'Copying:', suffix = 'Complete', length = 50)
        for i, fp in enumerate(file_prop_list):
            fp.copy()
            print_progress_bar(i + 1, len(file_prop_list), prefix = 'Copying:', suffix = 'Complete', length = 50)

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

    valid_file_props = list()
    invalid_file_props = list()
    file_list = get_files_in_dir(root)
    
    print_progress_bar(0, len(file_list), prefix = 'Searching:', suffix = 'Complete', length = 50)
    for i, file in enumerate(file_list):
        date_taken, parse_type = get_date_taken(file)
        if date_taken is None:
            file.replace_root_path(invalid_dest)
            invalid_file_props.append(file)
        else:
            file.replace_root_path(valid_dest)
            file.set_date_taken(date_taken)
            file.parse_method = parse_type
            valid_file_props.append(file)
        print_progress_bar(i + 1, len(file_list), prefix = 'Searching:', suffix = 'Complete', length = 50)

    output_str = find_and_remove_duplicates(valid_file_props)

    print(TermColors.OKGREEN, "Found {} good files!".format(len(valid_file_props)), TermColors.ENDC)
    for fp in valid_file_props:
        print(TermColors.OKGREEN, "{: <60} {: <20}{: <20}---> {}".format(fp.get_src_file_name(), fp.file_type, fp.parse_method.value, fp.get_dst_file_name()), TermColors.ENDC)

    print(TermColors.WARNING, output_str, TermColors.ENDC, end='')

    print(TermColors.FAIL, "Found {} bad files!".format(len(invalid_file_props)), TermColors.ENDC)
    for fp in invalid_file_props:
        fmod = FileModifiedParser(fp.src_file)
        date, parse_type = fmod.get_result()
        formatted_date = get_formatted_date(date)
        print(TermColors.FAIL, "{: <60}{: <20}---> {}".format(fp.get_src_file_name(), fp.file_type, formatted_date), TermColors.ENDC)

    if do_copy:
        copy_files(valid_file_props)
        copy_files(invalid_file_props)