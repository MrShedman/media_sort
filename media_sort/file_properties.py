#!/usr/bin/env python3

import os
import shutil
import mimetypes
from media_sort.parsers import ParseType
from media_sort.utils import format_date

class FileProperties:
    def __init__(self, original_path):
        self.src_file = original_path
        self.dst_file = original_path
        self.root_path = os.getcwd()

        self.size = os.path.getsize(self.src_file)

        self.date_taken = None
        self.parse_method = ParseType.ERROR
        self.file_type = mimetypes.guess_type(self.src_file)[0]
        if self.file_type is None:
            self.file_type = "Unknown file type"
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
        self.date_taken = format_date(date)
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