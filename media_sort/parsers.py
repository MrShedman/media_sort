#!/usr/bin/env python3

import os
import datetime
import exifread
from PIL import Image
from hachoir.core import config as HachoirConfig
HachoirConfig.quiet = True
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

class ParserBase:
    def __init__(self, parse_type):
        self.type = parse_type
        self.date = None

    def get_result(self):
        return self.date, self.type

class FileModifiedParser(ParserBase):
    def __init__(self, file_name):
        super().__init__(ParseType.FILEMOD)
        timestamp = os.path.getmtime(file_name)
        date = datetime.datetime.fromtimestamp(timestamp)
        self.date = check_valid_date(date)

class PillowParser(ParserBase):
    def __init__(self, file_name):
        super().__init__(ParseType.PILLOW)
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

class ExifReadParser(ParserBase):
    def __init__(self, file_name):
        super().__init__(ParseType.EXIFREAD)
        f = open(file_name, 'rb')

        tags = exifread.process_file(f, stop_tag="DateTimeOriginal", details=False)
        field = "EXIF DateTimeOriginal"

        if field in tags:
            self.date = parse_date(tags[field])
        else:
            self.date = None
        
        f.close()

class HachoirParser(ParserBase):
    def __init__(self, file_name):
        super().__init__(ParseType.HACHOIR)
        parser = createParser(file_name)
        if not parser:
            #print("Unable to parse file %s" % file_name)
            return None
        with parser:
            try:
                metadata = extractMetadata(parser)
            except Exception as err:
                #print("Metadata extraction error: %s" % err)
                metadata = None
        if not metadata:
            #print("Unable to extract metadata")
            return None
        meta = metadata.exportDictionary()
        date = get_value_in_nested_dict(meta, "Creation date")
        if date is not None:
            self.date = parse_date(date, format="%Y-%m-%d %H:%M:%S")
            