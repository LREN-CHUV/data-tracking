import logging
import re

from sqlalchemy.exc import IntegrityError

# dicom refers to pydicom library
import dicom
from dicom.errors import InvalidDicomError

from . import utils


#######################################################################################################################
# GLOBAL VARIABLES
#######################################################################################################################

conn = None


#######################################################################################################################
# PUBLIC FUNCTIONS
#######################################################################################################################


def dicom2db(file_path, file_type, is_copy, step_id, db_conn, sid_by_patient=False, pid_in_vid=False,
             visit_in_path=False, rep_in_path=False):
    """Extract some meta-data from a DICOM file and store in a DB.

    Arguments:
    :param file_path: File path.
    :param file_type: File type (should be 'DICOM').
    :param is_copy: Indicate if this file is a copy.
    :param step_id: Step ID
    :param db_conn: Database connection.
    :param sid_by_patient: Rarely, a data set might use study IDs which are unique by patient
    (not for the whole study).
    E.g.: LREN data. In such a case, you have to enable this flag. This will use PatientID + StudyID as a session ID.
    :param pid_in_vid: Rarely, a data set might mix patient IDs and visit IDs. E.g. : LREN data. In such a case, you
    to enable this flag. This will try to split PatientID into VisitID and PatientID.
    :param visit_in_path: Enable this flag to get the visit ID from the folder hierarchy instead of DICOM meta-data
    (e.g. can be useful for PPMI).
    :param rep_in_path: Enable this flag to get the repetition ID from the folder hierarchy instead of DICOM meta-data
    (e.g. can be useful for PPMI).
    :return: A dictionary containing the following IDs : participant_id, visit_id, session_id, sequence_type_id,
    sequence_id, repetition_id, file_id.
    """
    global conn
    conn = db_conn
    try:
        logging.info("Extracting DICOM headers from '%s'" % file_path)

        dcm = dicom.read_file(file_path)
        dataset = db_conn.get_dataset(step_id)

        participant_id = _extract_participant(dcm, dataset, pid_in_vid)
        if visit_in_path:
            visit_id = _extract_visit_from_path(dcm, file_path, pid_in_vid, sid_by_patient, dataset,
                                                participant_id)
        else:
            visit_id = _extract_visit(dcm, dataset, participant_id, sid_by_patient, pid_in_vid)
        session_id = _extract_session(dcm, visit_id)
        sequence_type_id = _extract_sequence_type(dcm)
        sequence_id = _extract_sequence(session_id, sequence_type_id)
        if rep_in_path:
            repetition_id = _extract_repetition_from_path(dcm, file_path, sequence_id)
        else:
            repetition_id = _extract_repetition(dcm, sequence_id)
        file_id = extract_dicom(file_path, file_type, is_copy, repetition_id, step_id)
        return {'participant_id': participant_id, 'visit_id': visit_id, 'session_id': session_id,
                'sequence_type_id': sequence_type_id, 'sequence_id': sequence_id, 'repetition_id': repetition_id,
                'file_id': file_id}
    except InvalidDicomError:
        logging.warning("%s is not a DICOM file !" % step_id)
    except IntegrityError:
        logging.warning("A problem occurred with the DB ! A rollback will be performed...")
        conn.db_session.rollback()


def extract_dicom(path, file_type, is_copy, repetition_id, processing_step_id):
    df = conn.db_session.query(conn.DataFile).filter_by(path=path).one_or_none()

    if not df:
        df = conn.DataFile(
            path=path,
            type=file_type,
            repetition_id=repetition_id,
            processing_step_id=processing_step_id,
            is_copy=is_copy
        )
        conn.db_session.add(df)
    else:
        df.file_type = file_type
        df.repetition_id = repetition_id
        df.processing_step_id = processing_step_id
        df.is_copy = is_copy
    conn.db_session.commit()

    return df.id


#######################################################################################################################
# PRIVATE FUNCTIONS
#######################################################################################################################


def _extract_participant(dcm, dataset, pid_in_vid=False):
    try:
        participant_name = dcm.PatientID
        if pid_in_vid:
            try:
                participant_name = utils.split_patient_id(participant_name)[1]
            except TypeError:
                pass
    except AttributeError:
        logging.warning("Patient ID was not found !")
        participant_name = None
    try:
        participant_birth_date = utils.format_date(dcm.PatientBirthDate)
    except AttributeError:
        logging.debug("Field PatientBirthDate was not found")
        participant_birth_date = None
    try:
        participant_gender = dcm.PatientSex
    except AttributeError:
        logging.debug("Field PatientSex was not found")
        participant_gender = None

    participant_id = conn.get_participant_id(participant_name, dataset)

    participant = conn.db_session.query(
        conn.Participant).filter_by(id=participant_id).one_or_none()

    if not participant:
        participant = conn.Participant(
            id=participant_id,
            gender=participant_gender,
            birth_date=participant_birth_date,
        )
        conn.db_session.add(participant)
    else:
        participant.gender = participant_gender
        participant.birth_date = participant_birth_date
    conn.db_session.commit()

    return participant.id


def _extract_visit(dcm, dataset, participant_id, by_patient=False, pid_in_vid=False):
    visit_name = None
    if pid_in_vid:  # If the patient ID and the visit ID are mixed into the PatientID field (e.g. LREN data)
        try:
            patient_id = dcm.PatientID
            if pid_in_vid:
                try:
                    visit_name = utils.split_patient_id(patient_id)[0]
                except TypeError:
                    pass
        except AttributeError:
            logging.warning("Patient ID was not found !")
            visit_name = None
    if not pid_in_vid or not visit_name:  # Otherwise, we use the StudyID (also used as a session ID) (e.g. PPMI data)
        try:
            visit_name = str(dcm.StudyID)
            if by_patient:  # If the Study ID is given at the patient level (e.g. LREN data), here is a little trick
                visit_name = str(dcm.PatientID) + "_" + visit_name
        except AttributeError:
            logging.debug("Field StudyID was not found")
            visit_name = None
    try:
        scan_date = utils.format_date(dcm.AcquisitionDate)
        if not scan_date:
            raise AttributeError
    except AttributeError:
        scan_date = utils.format_date(dcm.SeriesDate)  # If acquisition date is missing, we use the series date
    try:
        participant_age = utils.format_age(dcm.PatientAge)
    except AttributeError:
        logging.debug("Field PatientAge was not found")
        participant_age = None

    visit_id = conn.get_visit_id(visit_name, dataset)

    visit = conn.db_session.query(conn.Visit).filter_by(id=visit_id).one_or_none()

    if not visit:
        visit = conn.Visit(
            id=visit_id,
            date=scan_date,
            participant_id=participant_id,
            patient_age=participant_age
        )
        conn.db_session.add(visit)
    else:
        visit.date = scan_date
        visit.participant_id = participant_id
        visit.patient_age = participant_age
    conn.db_session.commit()

    return visit.id


def _extract_session(dcm, visit_id):
    try:
        session_value = str(dcm.StudyID)
    except AttributeError:
        logging.debug("Field StudyID was not found")
        session_value = None

    session = conn.db_session.query(conn.Session).filter_by(
        visit_id=visit_id, name=session_value).first()

    if not session:
        session = conn.Session(
            visit_id=visit_id,
            name=session_value,
        )
        conn.db_session.add(session)
        conn.db_session.commit()

    return session.id


def _extract_sequence_type(dcm):
    fields = _extract_sequence_type_fields(dcm)

    sequence_type = conn.db_session.query(conn.SequenceType).filter_by(
        name=fields['sequence_name'],
        manufacturer=fields['manufacturer'],
        manufacturer_model_name=fields['manufacturer_model_name'],
        institution_name=fields['institution_name'],
        slice_thickness=fields['slice_thickness'],
        repetition_time=fields['repetition_time'],
        echo_time=fields['echo_time'],
        echo_number=fields['echo_number'],
        number_of_phase_encoding_steps=fields['number_of_phase_encoding_steps'],
        percent_phase_field_of_view=fields['percent_phase_field_of_view'],
        pixel_bandwidth=fields['pixel_bandwidth'],
        flip_angle=fields['flip_angle'],
        rows=fields['rows'],
        columns=fields['columns'],
        magnetic_field_strength=fields['magnetic_field_strength'],
        space_between_slices=fields['space_between_slices'],
        echo_train_length=fields['echo_train_length'],
        percent_sampling=fields['percent_sampling'],
        pixel_spacing_0=fields['pixel_spacing_0'],
        pixel_spacing_1=fields['pixel_spacing_1']
    ).one_or_none()

    if not sequence_type:
        sequence_type = conn.SequenceType(
            name=fields['sequence_name'],
            manufacturer=fields['manufacturer'],
            manufacturer_model_name=fields['manufacturer_model_name'],
            institution_name=fields['institution_name'],
            slice_thickness=fields['slice_thickness'],
            repetition_time=fields['repetition_time'],
            echo_time=fields['echo_time'],
            echo_number=fields['echo_number'],
            number_of_phase_encoding_steps=fields['number_of_phase_encoding_steps'],
            percent_phase_field_of_view=fields['percent_phase_field_of_view'],
            pixel_bandwidth=fields['pixel_bandwidth'],
            flip_angle=fields['flip_angle'],
            rows=fields['rows'],
            columns=fields['columns'],
            magnetic_field_strength=fields['magnetic_field_strength'],
            space_between_slices=fields['space_between_slices'],
            echo_train_length=fields['echo_train_length'],
            percent_sampling=fields['percent_sampling'],
            pixel_spacing_0=fields['pixel_spacing_0'],
            pixel_spacing_1=fields['pixel_spacing_1']
        )
        conn.db_session.add(sequence_type)
        conn.db_session.commit()

    return sequence_type.id


def _extract_sequence_type_fields(dcm):
    fields = dict()
    try:
        fields['sequence_name'] = dcm.SeriesDescription  # It seems better to use this instead of ProtocolName
    except AttributeError:
        logging.debug("Field SeriesDescription was not found")
        try:
            fields['sequence_name'] = dcm.ProtocolName  # If SeriesDescription is missing, we use ProtocolName
        except AttributeError:
            fields['sequence_name'] = None
    try:
        fields['manufacturer'] = dcm.Manufacturer
    except AttributeError:
        logging.debug("Field Manufacturer was not found")
        fields['manufacturer'] = None
    try:
        fields['manufacturer_model_name'] = dcm.ManufacturerModelName
    except AttributeError:
        logging.debug("Field ManufacturerModelName was not found")
        fields['manufacturer_model_name'] = None
    try:
        fields['institution_name'] = dcm.InstitutionName
    except AttributeError:
        logging.debug("Field InstitutionName was not found")
        fields['institution_name'] = None
    try:
        fields['slice_thickness'] = float(dcm.SliceThickness)
    except (AttributeError, ValueError):
        logging.debug("Field SliceThickness was not found")
        fields['slice_thickness'] = None
    try:
        fields['repetition_time'] = float(dcm.RepetitionTime)
    except (AttributeError, ValueError):
        logging.debug("Field RepetitionTime was not found")
        fields['repetition_time'] = None
    try:
        fields['echo_time'] = float(dcm.EchoTime)
    except (AttributeError, ValueError):
        logging.debug("Field EchoTime was not found")
        fields['echo_time'] = None
    try:
        fields['number_of_phase_encoding_steps'] = int(dcm.NumberOfPhaseEncodingSteps)
    except (AttributeError, ValueError):
        logging.debug("Field NumberOfPhaseEncodingSteps was not found")
        fields['number_of_phase_encoding_steps'] = None
    try:
        fields['percent_phase_field_of_view'] = float(dcm.PercentPhaseFieldOfView)
    except (AttributeError, ValueError):
        logging.debug("Field PercentPhaseFieldOfView was not found")
        fields['percent_phase_field_of_view'] = None
    try:
        fields['pixel_bandwidth'] = int(dcm.PixelBandwidth)
    except (AttributeError, ValueError):
        logging.debug("Field PixelBandwidth was not found")
        fields['pixel_bandwidth'] = None
    try:
        fields['flip_angle'] = float(dcm.FlipAngle)
    except (AttributeError, ValueError):
        logging.debug("Field FlipAngle was not found")
        fields['flip_angle'] = None
    try:
        fields['rows'] = int(dcm.Rows)
    except (AttributeError, ValueError):
        logging.debug("Field Rows was not found")
        fields['rows'] = None
    try:
        fields['columns'] = int(dcm.Columns)
    except (AttributeError, ValueError):
        logging.debug("Field Columns was not found")
        fields['columns'] = None
    try:
        fields['magnetic_field_strength'] = float(dcm.MagneticFieldStrength)
    except (AttributeError, ValueError):
        logging.debug("Field MagneticFieldStrength was not found")
        fields['magnetic_field_strength'] = None
    try:
        fields['echo_train_length'] = int(dcm.EchoTrainLength)
    except (AttributeError, ValueError):
        logging.debug("Field EchoTrainLength was not found")
        fields['echo_train_length'] = None
    try:
        fields['percent_sampling'] = float(dcm.PercentSampling)
    except (AttributeError, ValueError):
        logging.debug("Field PercentSampling was not found")
        fields['percent_sampling'] = None
    try:
        pixel_spacing = dcm.PixelSpacing
    except AttributeError:
        logging.debug("Field PixelSpacing was not found")
        pixel_spacing = None
    try:
        fields['pixel_spacing_0'] = float(pixel_spacing[0])
    except (AttributeError, ValueError, TypeError):
        logging.debug("Field pixel_spacing0 was not found")
        fields['pixel_spacing_0'] = None
    try:
        fields['pixel_spacing_1'] = float(pixel_spacing[1])
    except (AttributeError, ValueError, TypeError):
        logging.debug("Field pixel_spacing1 was not found")
        fields['pixel_spacing_1'] = None
    try:
        fields['echo_number'] = int(dcm.EchoNumber)
    except (AttributeError, ValueError):
        logging.debug("Field echo_number was not found")
        fields['echo_number'] = None
    try:
        fields['space_between_slices'] = float(dcm[0x0018, 0x0088].value)
    except (AttributeError, ValueError, KeyError):
        logging.debug("Field space_between_slices was not found")
        fields['space_between_slices'] = None
    return fields


def _extract_sequence(session_id, sequence_type_id):
    name = conn.db_session.query(conn.SequenceType).filter_by(id=sequence_type_id).one_or_none().name
    sequence = conn.db_session.query(conn.Sequence).filter_by(session_id=session_id, name=name).one_or_none()

    if not sequence:
        sequence = conn.Sequence(
            name=name,
            session_id=session_id,
            sequence_type_id=sequence_type_id,
        )
        conn.db_session.add(sequence)

    else:
        sequence.sequence_type_id = sequence_type_id
    conn.db_session.commit()

    return sequence.id


def _extract_repetition(dcm, sequence_id):
    try:
        repetition_name = str(dcm.SeriesNumber)
    except AttributeError:
        logging.warning("Field SeriesNumber was not found")
        repetition_name = None
    try:
        series_date = utils.format_date(dcm.SeriesDate)
        if not series_date:
            raise AttributeError
    except AttributeError:
        series_date = None

    repetition = conn.db_session.query(conn.Repetition).filter_by(
        sequence_id=sequence_id, name=repetition_name).one_or_none()

    if not repetition:
        repetition = conn.Repetition(
            sequence_id=sequence_id,
            name=repetition_name,
            date=series_date
        )
        conn.db_session.add(repetition)
    else:
        repetition.date = series_date
    conn.db_session.commit()

    return repetition.id


def _extract_visit_from_path(dcm, file_path, pid_in_vid, by_patient, dataset, participant_id):
    visit_name = None
    if pid_in_vid:  # If the patient ID and the visit ID are mixed into the PatientID field (e.g. LREN data)
        try:
            patient_name = dcm.PatientID
            if pid_in_vid:
                try:
                    visit_name = utils.split_patient_id(patient_name)[0]
                except TypeError:
                    pass
        except AttributeError:
            logging.warning("Patient ID was not found !")
            visit_name = None
    if not pid_in_vid or not visit_name:  # Otherwise, we use the StudyID (also used as a session ID) (e.g. PPMI data)
        try:
            visit_name = str(re.findall('/([^/]+?)/[^/]+?/[^/]+?/[^/]+?\.dcm', file_path)[0])
            if by_patient:  # If the Study ID is given at the patient level (e.g. LREN data), here is a little trick
                visit_name = dcm.PatientID + "_" + visit_name
        except AttributeError:
            logging.debug("Field StudyID or PatientID was not found")
            visit_name = None
    try:
        scan_date = utils.format_date(dcm.AcquisitionDate)
        if not scan_date:
            raise AttributeError
    except AttributeError:
        scan_date = utils.format_date(dcm.SeriesDate)  # If acquisition date is missing, we use the series date

    visit_id = conn.get_visit_id(visit_name, dataset)

    visit = conn.db_session.query(conn.Visit).filter_by(id=visit_id).one_or_none()

    if not visit:
        visit = conn.Visit(
            id=visit_id,
            date=scan_date,
            participant_id=participant_id,
        )
        conn.db_session.add(visit)
    else:
        visit.date = scan_date
        visit.participant_id = participant_id
        conn.db_session.commit()

    return visit.id


def _extract_repetition_from_path(dcm, file_path, sequence_id):
    repetition_name = str(re.findall('/([^/]+?)/[^/]+?\.dcm', file_path)[0])
    try:
        series_date = utils.format_date(dcm.SeriesDate)
        if not series_date:
            raise AttributeError
    except AttributeError:
        series_date = None

    repetition = conn.db_session.query(conn.Repetition).filter_by(
        sequence_id=sequence_id, name=repetition_name).one_or_none()

    if not repetition:
        repetition = conn.Repetition(
            sequence_id=sequence_id,
            name=repetition_name,
            date=series_date
        )
        conn.db_session.add(repetition)
    else:
        repetition.date = series_date
        conn.db_session.commit()

    return repetition.id
