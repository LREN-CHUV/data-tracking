#!/usr/bin/env python3.5


########################################################################################################################
# IMPORTS
########################################################################################################################

import argparse
import csv
import pandas
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import exc

from pymysql import err


########################################################################################################################
# CONSTANTS
########################################################################################################################

PR_ID_COLUMN = "Subject ID"
HANDEDNESS_COLUMN = "Handedness"
ROLE_COLUMN = "Control (C) / Patient=non Control (P) / Incidental Finding (IC)"
SCAN_DATE_COLUMN = "Study Date"
PARTICIPANT_COLUMNS = [PR_ID_COLUMN, HANDEDNESS_COLUMN]
SCAN_COLUMNS = [PR_ID_COLUMN, SCAN_DATE_COLUMN, ROLE_COLUMN]


########################################################################################################################
# FUNCTIONS - MAIN
########################################################################################################################

def main():
    logging.basicConfig(level='INFO')
    args = parse_args()

    logging.info("[START]")

    logging.info("Connecting to DB")
    db = init_db(args.db)
    db_session = db["session"]
    participant_class = db["participant_class"]
    scan_class = db["scan_class"]

    data = pandas.read_excel(args.input_file, args.input_sheet)

    search_handedness(data, db_session, participant_class, args.id)
    search_role(data, db_session, scan_class, args.id)

    logging.info("[DONE]")


########################################################################################################################
# FUNCTIONS - UTILS
########################################################################################################################

def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('input_sheet')
    parser.add_argument('db')
    parser.add_argument(
        "-i",
        "--id",
        help="path to CSV file containing unique participants IDs"
    )
    return parser.parse_args()


def format_date(timestamp):
    return timestamp.strftime('%Y-%m-%d')


def print_db_except():
    logging.warning("A problem occurred while trying to insert data into DB.")
    logging.warning("This can be caused by a duplicate entry on a unique field.")
    logging.warning("A rollback will be performed !")


def search_handedness(data, db_session, participant_class, id_file=None):
    participants_data = data[PARTICIPANT_COLUMNS].drop_duplicates(subset=PR_ID_COLUMN)
    for db_participant in db_session.query(participant_class):
        logging.info("Processing participant %s..." % db_participant.id)
        for row in participants_data.itertuples():
            pid = row[1]
            if id_file:
                pid = get_anonym_id(id_file, pid)
            handedness = row[2]
            if pid == db_participant.id:
                if pandas.notnull(handedness):
                    try:
                        db_participant.handedness = handedness
                        db_session.add(db_participant)
                        db_session.commit()
                    except (err.IntegrityError, exc.IntegrityError):
                        print_db_except()
                        db_session.rollback()


def search_role(data, db_session, scan_class, id_file=None):
    scans_data = data[SCAN_COLUMNS].drop_duplicates(subset=PR_ID_COLUMN)
    for db_scan in db_session.query(scan_class):
        logging.info("Processing scan %s..." % db_scan.id)
        for row in scans_data.itertuples():
            pid = row[1]
            if id_file:
                pid = get_anonym_id(id_file, pid)
            scan_date = format_date(row[2])
            role = row[3]
            if pandas.notnull(role) and pid == db_scan.participant_id and scan_date == str(db_scan.date):
                try:
                    db_scan.role = role
                    db_session.add(db_scan)
                    db_session.commit()
                except (err.IntegrityError, exc.IntegrityError):
                    print_db_except()
                    db_session.rollback()


def get_anonym_id(id_file, old_id):

    try:
        with open(id_file, 'r') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                if row[0] == old_id:
                    return row[1]
    except FileNotFoundError:
        logging.warning("ID file not found !")

    return None


########################################################################################################################
# FUNCTIONS - DATABASE
########################################################################################################################

def init_db(db):

    base_class = automap_base()
    engine = create_engine(db)
    base_class.prepare(engine, reflect=True)

    participant_class = base_class.classes.participant
    scan_class = base_class.classes.scan

    return {
        "session": Session(engine),
        "participant_class": participant_class,
        "scan_class": scan_class
    }


########################################################################################################################
# ENTRY POINT
########################################################################################################################

if __name__ == '__main__':

    main()
