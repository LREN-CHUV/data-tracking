##########################################################################
# IMPORTS
##########################################################################

import logging
import re
import glob
import os

from . import connection
from datetime import date


##########################################################################
# GLOBAL
##########################################################################

ARGS = ['root_folder', 'csv', 'db']

conn = None


##########################################################################
# FUNCTIONS - NIFTI
##########################################################################

def nifti2db(folder, participant_id, scan_date, files_pattern='**/*.nii', db_url=None):
    """
    Extract some meta-data from nifti files based on their paths and file names
    :param folder: root folder
    :param participant_id: participant ID
    :param scan_date: scan date
    :param files_pattern: Nifti files pattern (default is '**/*.nii')
    :param db_url: DB URL, if not defined it will try to find an Airflow configuration file
    :return:
    """
    global conn
    conn = connection.Connection(db_url)
    for file_path in glob.iglob(os.path.join(folder, files_pattern), recursive=True):
        logging.info("Processing '%s'" % file_path)
        try:
            session = str(re.findall(
                '/([^/]+?)/[^/]+?/[^/]+?/[^/]+?\.nii', file_path)[0])
            sequence = re.findall(
                '/([^/]+?)/[^/]+?/[^/]+?\.nii', file_path)[0]
            repetition = int(re.findall(
                '/([^/]+?)/[^/]+?\.nii', file_path)[0])

            logging.info("SEQUENCE : " + sequence)

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
            logging.warning(
                "A problem occurred with '%s' ! Check the path format... " % file_path)

    conn.close()
    logging.info('[FINISH]')


##########################################################################
# FUNCTIONS - UTILS
##########################################################################

def date_from_str(date_str):
    day = int(re.findall('(\d+)\.\d+\.\d+', date_str)[0])
    month = int(re.findall('\d+\.(\d+)\.\d+', date_str)[0])
    year = int(re.findall('\d+\.\d+\.(\d+)', date_str)[0])
    return date(year, month, day)


##########################################################################
# FUNCTIONS - DATABASE
##########################################################################

def save_nifti_meta(
        participant_id,
        scan_date,
        session,
        sequence,
        repetition,
        prefix_type,
        postfix_type,
        file_path
):
    if not conn.db_session.query(conn.DataFile).filter_by(path=file_path).first():

        scan = conn.db_session.query(conn.Scan).filter_by(date=scan_date, participant_id=participant_id)\
            .first()
        sequence_type_list = conn.db_session.query(
            conn.SequenceType).filter_by(name=sequence).all()

        if scan and len(sequence_type_list) > 0:
            scan_id = scan.id
            sess = conn.db_session.query(conn.Session).filter_by(
                scan_id=scan_id, value=session).first()

            if sess:
                session_id = sess.id
                if len(sequence_type_list) > 1:
                    logging.warning(
                        "Multiple sequence_type available for %s !" % sequence)
                sequence_type_id = sequence_type_list[0].id
                seq = conn.db_session.query(conn.Sequence).filter_by(
                    session_id=session_id,
                    sequence_type_id=sequence_type_id)\
                    .first()

                if seq:
                    sequence_id = seq.id
                    rep = conn.db_session.query(conn.Repetition).filter_by(
                        sequence_id=sequence_id,
                        value=repetition)\
                        .first()

                    if rep:
                        repetition_id = rep.id
                        nii = conn.DataFile(
                            repetition_id=repetition_id,
                            path=file_path,
                            type='nifti',
                            result_type=prefix_type,
                            output_type=postfix_type
                        )
                        conn.db_session.add(nii)
                        conn.db_session.commit()
