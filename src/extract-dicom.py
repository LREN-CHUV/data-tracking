#!/usr/bin/env python3.5


########################################################################################################################
# IMPORTS
########################################################################################################################

import argparse
import glob
import dicom
import datetime
import csv
import logging
import os
import time

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import exc

from pymysql import err
from dicom.errors import InvalidDicomError


########################################################################################################################
# CONSTANTS
########################################################################################################################

DEFAULT_HANDEDNESS = 'unknown'
DEFAULT_ROLE = 'U'
DEFAULT_COMMENT = ''


########################################################################################################################
# FUNCTIONS - MAIN
########################################################################################################################

def main():
    logging.basicConfig(level='INFO')
    args = parse_args()

    logging.debug("[START]")
    start_time = time.clock()

    logging.info("Connecting to DB")
    db = init_db(args.db)
    db_session = db["session"]
    participant_class = db["participant_class"]
    scan_class = db["scan_class"]
    dicom_class = db["dicom_class"]
    session_class = db["session_class"]
    sequence_type_class = db["sequence_type_class"]
    sequence_class = db["sequence_class"]
    repetition_class = db["repetition_class"]

    checked_folders = dict()
    count_files = 0

    for filename in glob.iglob(args.root + '/**/MR.*', recursive=True):
        try:
            logging.debug("Processing '%s'" % filename)
            count_files += 1
            folder = os.path.split(filename)[0]

            if folder not in checked_folders:
                logging.info("Extracting DICOM headers from '%s'" % filename)
                ds = dicom.read_file(filename)

                participant_id = extract_participant(participant_class, ds, db_session, DEFAULT_HANDEDNESS, args.id)
                scan_id = extract_scan(scan_class, ds, db_session, participant_id, DEFAULT_ROLE, DEFAULT_COMMENT)
                session_id = extract_session(session_class, ds, db_session, scan_id)
                sequence_type_id = extract_sequence_type(sequence_type_class, ds, db_session)
                sequence_id = extract_sequence(sequence_class, db_session, session_id, sequence_type_id)
                repetition_id = extract_repetition(repetition_class, ds, db_session, sequence_id)

                checked_folders[folder] = repetition_id
            extract_dicom(dicom_class, db_session, filename, checked_folders[folder])

        except (InvalidDicomError, IsADirectoryError):
            logging.warning("%s is not a DICOM file !" % filename)

        except (err.IntegrityError, exc.IntegrityError):
            print_db_except()
            db_session.rollback()

    stop_time = time.clock()
    logging.debug("[DONE]")

    logging.info("Closing DB connection")
    db_session.close()

    duration = stop_time - start_time
    logging.debug("Processed %s files in %s" % (str(count_files), str(duration)))


########################################################################################################################
# FUNCTIONS - UTILS
########################################################################################################################

def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument('root')
    parser.add_argument('db')
    parser.add_argument(
        "-i",
        "--id",
        help="path to CSV file containing unique participants IDs"
    )
    return parser.parse_args()


def format_date(date):
    return datetime.datetime(int(date[:4]), int(date[4:6]), int(date[6:8]))


def format_gender(gender):
    if gender == 'M':
        return 'male'
    elif gender == 'F':
        return 'female'
    else:
        return 'unknown'


def print_db_except():
    logging.warning("A problem occurred while trying to insert data into DB.")
    logging.warning("This can be caused by a duplicate entry on a unique field.")
    logging.warning("A rollback will be performed !")


########################################################################################################################
# FUNCTIONS - CSV
########################################################################################################################

def read_anonym_id(id_file, old_id):

    try:
        with open(id_file, 'r') as f:
            csv_reader = csv.reader(f)
            return next((row[1] for row in csv_reader if row[0] == old_id), None)
    except FileNotFoundError:
        logging.warning("ID file not found !")


########################################################################################################################
# FUNCTIONS - DATABASE
########################################################################################################################

def init_db(db):

    base_class = automap_base()
    engine = create_engine(db)
    base_class.prepare(engine, reflect=True)

    participant_class = base_class.classes.participant
    scan_class = base_class.classes.scan
    dicom_class = base_class.classes.dicom
    session_class = base_class.classes.session
    sequence_type_class = base_class.classes.sequence_type
    sequence_class = base_class.classes.sequence
    repetition_class = base_class.classes.repetition

    return {
        "session": Session(engine),
        "participant_class": participant_class,
        "scan_class": scan_class,
        "dicom_class": dicom_class,
        "session_class": session_class,
        "sequence_type_class": sequence_type_class,
        "sequence_class": sequence_class,
        "repetition_class": repetition_class
    }


def extract_participant(participant_class, ds, db_session, handedness, id_file):
    if id_file:
        old_id = ds.PatientID
        participant_id = read_anonym_id(id_file, old_id)
    else:
        participant_id = ds.PatientID

    participant_birth_date = format_date(ds.PatientBirthDate)
    participant_gender = format_gender(ds.PatientSex)

    if participant_id is None:
        logging.warning("participant cannot be saved because no ID was found !")
        return None
    else:
        participant = db_session.query(participant_class).filter_by(id=participant_id).first()

        if not participant:
            participant = participant_class(
                id=participant_id,
                gender=participant_gender,
                handedness=handedness,
                birthdate=participant_birth_date
            )
            db_session.add(participant)
            db_session.commit()

    return participant.id


def extract_scan(scan_class, ds, db_session, participant_id, role, comment):

    scan_date = format_date(ds.StudyDate)

    scan = db_session.query(scan_class).filter_by(participant_id=participant_id, date=scan_date).first()

    if not scan:
        scan = scan_class(
            date=scan_date,
            role=role,
            comment=comment,
            participant_id=participant_id
        )
        db_session.add(scan)
        db_session.commit()

    return scan.id


def extract_session(session_class, ds, db_session, scan_id):

    session_value = int(ds.StudyID)

    session = db_session.query(session_class).filter_by(scan_id=scan_id, value=session_value).first()

    if not session:
        session = session_class(
            scan_id=scan_id,
            value=session_value
        )
        db_session.add(session)
        db_session.commit()

    return session.id


def extract_sequence_type(sequence_type_class, ds, db_session):

    sequence_name = ds.ProtocolName
    manufacturer = ds.Manufacturer
    manufacturer_model_name = ds.ManufacturerModelName
    institution_name = ds.InstitutionName
    slice_thickness = float(ds.SliceThickness)
    repetition_time = float(ds.RepetitionTime)
    echo_time = float(ds.EchoTime)
    number_of_phase_encoding_steps = int(ds.NumberOfPhaseEncodingSteps)
    percent_phase_field_of_view = float(ds.PercentPhaseFieldOfView)
    pixel_bandwidth = int(ds.PixelBandwidth)
    flip_angle = float(ds.FlipAngle)
    rows = int(ds.Rows)
    columns = int(ds.Columns)
    magnetic_field_strength = float(ds.MagneticFieldStrength)
    echo_train_length = int(ds.EchoTrainLength)
    percent_sampling = float(ds.PercentSampling)
    pixel_spacing = ds.PixelSpacing
    pixel_spacing_0 = float(pixel_spacing[0])
    pixel_spacing_1 = float(pixel_spacing[1])

    try:
        echo_number = int(ds.EchoNumber)
    except AttributeError:
        echo_number = int(0)
    try:
        space_between_slices = float(ds[0x0018, 0x0088].value)
    except KeyError:
        space_between_slices = float(0.0)

    sequence_type_list = db_session.query(sequence_type_class).filter_by(
        name=sequence_name,
        manufacturer=manufacturer,
        manufacturer_model_name=manufacturer_model_name,
        institution_name=institution_name,
        echo_number=echo_number,
        number_of_phase_encoding_steps=number_of_phase_encoding_steps,
        pixel_bandwidth=pixel_bandwidth,
        rows=rows,
        columns=columns,
        echo_train_length=echo_train_length
    ).all()

    sequence_type_list = list(filter(lambda s: not (
        s.slice_thickness != str(slice_thickness)
        or str(s.repetition_time) != str(repetition_time)
        or str(s.echo_time) != str(echo_time)
        or str(s.percent_phase_field_of_view) != str(percent_phase_field_of_view)
        or str(s.flip_angle) != str(flip_angle)
        or str(s.magnetic_field_strength) != str(magnetic_field_strength)
        or str(s.flip_angle) != str(flip_angle)
        or str(s.percent_sampling) != str(percent_sampling)
        or str(s.pixel_spacing_0) != str(pixel_spacing_0)
        or str(s.pixel_spacing_1) != str(pixel_spacing_1)
        ), sequence_type_list))

    if len(sequence_type_list) > 0:
        sequence_type = sequence_type_list[0]
    else:
        sequence_type = sequence_type_class(
            name=sequence_name,
            manufacturer=manufacturer,
            manufacturer_model_name=manufacturer_model_name,
            institution_name=institution_name,
            slice_thickness=slice_thickness,
            repetition_time=repetition_time,
            echo_time=echo_time,
            echo_number=echo_number,
            number_of_phase_encoding_steps=number_of_phase_encoding_steps,
            percent_phase_field_of_view=percent_phase_field_of_view,
            pixel_bandwidth=pixel_bandwidth,
            flip_angle=flip_angle,
            rows=rows,
            columns=columns,
            magnetic_field_strength=magnetic_field_strength,
            space_between_slices=space_between_slices,
            echo_train_length=echo_train_length,
            percent_sampling=percent_sampling,
            pixel_spacing_0=pixel_spacing_0,
            pixel_spacing_1=pixel_spacing_1
        )
        db_session.add(sequence_type)
        db_session.commit()

    return sequence_type.id


def extract_sequence(sequence_class, db_session, session_id, sequence_type_id):

    sequence = db_session.query(sequence_class)\
        .filter_by(session_id=session_id, sequence_type_id=sequence_type_id)\
        .first()

    if not sequence:
        sequence = sequence_class(
            session_id=session_id,
            sequence_type_id=sequence_type_id
        )
        db_session.add(sequence)
        db_session.commit()

    return sequence.id


def extract_repetition(repetition_class, ds, db_session, sequence_id):

    repetition_value = int(ds.SeriesNumber)

    repetition = db_session.query(repetition_class).filter_by(sequence_id=sequence_id, value=repetition_value).first()

    if not repetition:
        repetition = repetition_class(
            sequence_id=sequence_id,
            value=repetition_value
        )
        db_session.add(repetition)
        db_session.commit()

    return repetition.id


def extract_dicom(dicom_class, db_session, path, repetition_id):

    dcm = db_session.query(dicom_class).filter_by(path=path, repetition_id=repetition_id).first()

    if not dcm:
        dcm = dicom_class(
            path=path,
            repetition_id=repetition_id
        )
        db_session.add(dcm)
        db_session.commit()

    return dcm.id


########################################################################################################################
# ENTRY POINT
########################################################################################################################

if __name__ == '__main__':

    main()
