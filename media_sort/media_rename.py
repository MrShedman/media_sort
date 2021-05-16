#!/usr/bin/env python3

import os
import argparse
import datetime

from media_sort.file_properties import get_files_in_dir
from media_sort.utils import format_date, TermColors

def modify_date(dt, year=None, month=None, day=None):
    kwargs = {}
    if year  : kwargs['year']  = int(year)
    if month : kwargs['month'] = int(month)
    if day   : kwargs['day'] = int(day)
    if kwargs : return dt.replace(**kwargs)
    else      : return dt

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-year", "-y")
    parser.add_argument("-month", "-m")
    parser.add_argument("-day", "-d")
    parser.add_argument("-rename", "-rn", action='store_true')

    args = parser.parse_args()

    do_rename = args.rename

    if args.year:
        print(TermColors.OKGREEN, "Change year to {}".format(args.year), TermColors.ENDC)
    if args.month:
        print(TermColors.OKGREEN, "Change month to {}".format(args.month), TermColors.ENDC)
    if args.day:
        print(TermColors.OKGREEN, "Change day to {}".format(args.day), TermColors.ENDC)

    file_list = get_files_in_dir(os.getcwd())

    for i, file in enumerate(file_list):
        name, ext = os.path.splitext(os.path.basename(file.src_file))
        date = datetime.datetime.strptime(name, "%Y_%m_%d_%H_%M_%S")
        date = modify_date(date, args.year, args.month, args.day)
        file.set_date_taken(date)
        print("{: <60}--->{}".format(file.get_src_file_name(), file.get_dst_file_name()))
        if do_rename:
            os.rename(file.src_file, file.dst_file)