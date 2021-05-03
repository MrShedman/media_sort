#!/usr/bin/env python3

import os
import datetime
import exifread
from PIL import Image
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from enum import Enum
from media_sort.utils import get_value_in_nested_dict

class ParseType(Enum):   
    EXIFREAD = "exifread"
    PILLOW = "Pillow"
    HACHOIR = "hachoir"
    FILEMOD = "File Modified"
    ERROR = "No date found"

valid_date_limit = datetime.datetime.strptime("2000:01:01 00:00:00", "%Y:%m:%d %H:%M:%S")

def check_valid_date(date):
    if date > valid_date_limit:
        return date
    else:
        return None

def parse_date(date, format = "%Y:%m:%d %H:%M:%S"):
    date_obj = None
    try:
        date_obj = datetime.datetime.strptime(str(date), format)
    except:
        return None
    else: 
        return check_valid_date(date_obj)

class FileModifiedParser:
    def __init__(self, file_name):
        self.type = ParseType.FILEMOD
        timestamp = os.path.getmtime(file_name)
        date = datetime.datetime.fromtimestamp(timestamp)
        self.date = check_valid_date(date)

    def get_result(self):
        return self.date, self.type

class PillowParser:
    def __init__(self, file_name):
        self.type = ParseType.PILLOW
        exif = Image.open(file_name).getexif()
        tags = [36867, 306]
        dates = list()
        for tag in tags:
            if tag in exif:
                dates.append(parse_date(exif[tag]))
        if len(dates) > 1:
            dates_sorted = sorted(dates, key=lambda x: (x is None, x))
            self.date = dates_sorted[0]
        elif len(dates) > 0:
            self.date = dates[0]
        else:
            self.date = None

    def get_result(self):
        return self.date, self.type

class ExifReadParser:
    def __init__(self, file_name):
        self.type = ParseType.EXIFREAD
        f = open(file_name, 'rb')

        tags = exifread.process_file(f, stop_tag="DateTimeOriginal", details=False)
        field = "EXIF DateTimeOriginal"

        if field in tags:
            self.date = parse_date(tags[field])
        else:
            self.date = None
        
        f.close()

    def get_result(self):
        return self.date, self.type

class HachoirParser:
    def __init__(self, file_name):
        self.type = ParseType.HACHOIR
        self.date = None

        parser = createParser(file_name)
        if not parser:
            print("Unable to parse file %s" % file_name)
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
            self.date = parse_date(date, format="%Y-%m-%d %H:%M:%S")

    def get_result(self):
        return self.date, self.type