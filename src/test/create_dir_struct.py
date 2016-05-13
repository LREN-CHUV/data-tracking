#!/usr/bin/env python3.5


########################################################################################################################
# IMPORTS
########################################################################################################################

import logging
import argparse
import csv
import os


########################################################################################################################
# CONSTANTS
########################################################################################################################

ARGS = ['csv']
IN_PREFIX = "M:/CRN/LREN/SHARE/VBQ_Output_All/MPMs_All/"
OUT_PREFIX = "./data/"


########################################################################################################################
# FUNCTIONS - MAIN
########################################################################################################################

def main():
    logging.basicConfig(level='INFO')
    logging.info('[START]')
    args = parse_args(ARGS)

    with open(args.csv, 'r') as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            path = str(row[0])
            if path[len(path)-4:] == ".nii":
                path = OUT_PREFIX + path[len(IN_PREFIX):].replace('\\', '/')
                logging.info("processing: " + path)
                directory = os.path.dirname(path)
                if not os.path.exists(directory):
                    os.makedirs(directory)
                with open(path, 'w') as out:
                    out.write("FAKE")

    logging.info('[FINISH]')


########################################################################################################################
# FUNCTIONS - UTILS
########################################################################################################################

def parse_args(args):
    parser = argparse.ArgumentParser()
    for arg in args:
        parser.add_argument(arg)
    return parser.parse_args()


########################################################################################################################
# ENTRY POINT
########################################################################################################################

if __name__ == '__main__':
    main()
