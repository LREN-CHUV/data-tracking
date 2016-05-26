#!/usr/bin/env python3.5


########################################################################################################################
# IMPORTS
########################################################################################################################

import logging
import argparse
import os
import fnmatch
import re
import csv

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

from os import path


########################################################################################################################
# CONSTANTS
########################################################################################################################

ARGS = ['root_folder', 'csv', 'db']


########################################################################################################################
# FUNCTIONS - MAIN
########################################################################################################################

def main():
    logging.basicConfig(level='INFO')
    logging.info('[START]')
    args = parse_args(ARGS)
    logging.info('root_folder is set to ' + args.root_folder)

    logging.info("Connecting to DB")
    db = init_db(args.db)
    db_session = db["session"]
    scan_class = db["scan_class"]
    nifti_class = db["nifti_class"]
    session_class = db["session_class"]
    sequence_type_class = db["sequence_type_class"]
    sequence_class = db["sequence_class"]
    repetition_class = db["repetition_class"]

    logging.info("processing files... (This can take a few minutes)")
    for root, dirnames, filenames in os.walk(args.root_folder):
        for file in fnmatch.filter(filenames, '*.nii'):
            file_path = root+"/"+file
            file_path = path.abspath(file_path)
            logging.debug('processing: %s', file_path)

            try:
                pr_id = re.findall('/([^/]+?)/[^/]+?/[^/]+?/[^/]+?/[^/]+?\.nii', file_path)[0]
                session = int(re.findall('/([^/]+?)/[^/]+?/[^/]+?/[^/]+?\.nii', file_path)[0])
                sequence = re.findall('/([^/]+?)/[^/]+?/[^/]+?\.nii', file_path)[0]
                repetition = int(re.findall('/([^/]+?)/[^/]+?\.nii', file_path)[0])

                participant_id = None
                scan_date = None

                with open(args.csv, 'r') as f:
                    csv_reader = csv.reader(f)
                    for row in csv_reader:
                        if row[0] == pr_id:
                            participant_id = row[1]
                            scan_date = date_from_str(row[2])

                if participant_id and scan_date:

                    filename = re.findall('/([^/]+?)\.nii', file_path)[0]

                    try:
                        prefix_type = re.findall('(.*)PR', filename)[0]
                    except IndexError:
                        prefix_type = "unknown"

                    try:
                        postfix_type = re.findall('-\d\d_(.+)', filename)[0]
                    except IndexError:
                        postfix_type = "unknown"

                    save_nifti_meta(
                        db_session,
                        scan_class,
                        nifti_class,
                        session_class,
                        sequence_type_class,
                        sequence_class,
                        repetition_class,
                        participant_id,
                        scan_date,
                        session,
                        sequence,
                        repetition,
                        prefix_type,
                        postfix_type,
                        file_path
                    )

            except ValueError:
                logging.warning("A problem occurred with '%s' ! Check the path format... " % file_path)

    logging.info('[FINISH]')


########################################################################################################################
# FUNCTIONS - UTILS
########################################################################################################################

def parse_args(args):
    parser = argparse.ArgumentParser()
    for arg in args:
        parser.add_argument(arg)
    return parser.parse_args()


def date_from_str(date_str):
    day = int(re.findall('(\d+)\.\d+\.\d+', date_str)[0])
    month = int(re.findall('\d+\.(\d+)\.\d+', date_str)[0])
    year = int(re.findall('\d+\.\d+\.(\d+)', date_str)[0])
    return date(year, month, day)


########################################################################################################################
# FUNCTIONS - DATABASE
########################################################################################################################

def init_db(db):

    base_class = automap_base()
    engine = create_engine(db)
    base_class.prepare(engine, reflect=True)

    scan_class = base_class.classes.scan
    nifti_class = base_class.classes.nifti
    session_class = base_class.classes.session
    sequence_type_class = base_class.classes.sequence_type
    sequence_class = base_class.classes.sequence
    repetition_class = base_class.classes.repetition

    return {
        "session": Session(engine),
        "scan_class": scan_class,
        "nifti_class": nifti_class,
        "session_class": session_class,
        "sequence_type_class": sequence_type_class,
        "sequence_class": sequence_class,
        "repetition_class": repetition_class
    }


def save_nifti_meta(
        db_session,
        scan_class,
        nifti_class,
        session_class,
        sequence_type_class,
        sequence_class,
        repetition_class,
        participant_id,
        scan_date,
        session,
        sequence,
        repetition,
        prefix_type,
        postfix_type,
        file_path
):

    if not db_session.query(nifti_class).filter_by(path=file_path).first():

        scan = db_session.query(scan_class).filter_by(date=scan_date, participant_id=participant_id).first()
        sequence_type_list = db_session.query(sequence_type_class).filter_by(name=sequence).all()

        if scan and len(sequence_type_list) > 0:
            scan_id = scan.id
            sess = db_session.query(session_class).filter_by(scan_id=scan_id, value=session).first()

            if sess:
                session_id = sess.id
                if len(sequence_type_list) > 1:
                    logging.warning("Multiple sequence_type available for %s !" % sequence)
                sequence_type_id = sequence_type_list[0].id
                seq = db_session.query(sequence_class).filter_by(session_id=session_id,
                                                                 sequence_type_id=sequence_type_id).first()

                if seq:
                    sequence_id = seq.id
                    rep = db_session.query(repetition_class).filter_by(sequence_id=sequence_id, value=repetition)\
                        .first()

                    if rep:
                        repetition_id = rep.id
                        nii = nifti_class(
                            repetition_id=repetition_id,
                            path=file_path,
                            result_type=prefix_type,
                            output_type=postfix_type
                        )
                        db_session.add(nii)
                        db_session.commit()


########################################################################################################################
# ENTRY POINT
########################################################################################################################

if __name__ == '__main__':
    main()
