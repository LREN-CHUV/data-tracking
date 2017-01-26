import dicom
import datetime
import logging

from sqlalchemy.exc import IntegrityError
from dicom.errors import InvalidDicomError


########################################################################################################################
# SETTINGS
########################################################################################################################

DEFAULT_HANDEDNESS = 'unknown'
DEFAULT_ROLE = 'U'
DEFAULT_GENDER = 'unknown'
DEFAULT_PARTICIPANT_ID = 'unknown'
DEFAULT_COMMENT = ''
DEFAULT_SESSION_VALUE = 'unknown'
DEFAULT_REPETITION = 0

MALE_GENDER_LIST = ['m', 'male', 'man', 'boy']
FEMALE_GENDER_LIST = ['f', 'female', 'woman', 'girl']
MALE = 'male'
FEMALE = 'female'

conn = None


########################################################################################################################
# MAIN FUNCTIONS
########################################################################################################################

def dicom2db(file_path, file_type, is_copy, step_id, db_conn):
    """
    Extract some meta-data from a DICOM file and store in a DB.
    :param file_path: File path.
    :param file_type: File type (should be 'DICOM').
    :param is_copy: Indicate if this file is a copy.
    :param step_id: Step ID
    :param db_conn: Database connection.
    :return: A dictionary containing the following IDs : participant_id, scan_id, session_id, sequence_type_id,
    sequence_id, repetition_id, file_id.
    """
    global conn
    conn = db_conn
    try:
        logging.info("Extracting DICOM headers from '%s'" % file_path)
        ds = dicom.read_file(file_path)
        participant_id = extract_participant(ds, DEFAULT_HANDEDNESS)
        scan_id = extract_scan(ds, participant_id, DEFAULT_ROLE, DEFAULT_COMMENT)
        session_id = extract_session(ds, scan_id)
        sequence_type_id = extract_sequence_type(ds)
        sequence_id = extract_sequence(session_id, sequence_type_id)
        repetition_id = extract_repetition(ds, sequence_id)
        file_id = extract_dicom(file_path, file_type, is_copy, repetition_id, step_id)
        return {'participant_id': participant_id, 'scan_id': scan_id, 'session_id': session_id,
                'sequence_type_id': sequence_type_id, 'sequence_id': sequence_id, 'repetition_id': repetition_id,
                'file_id': file_id}
    except InvalidDicomError:
        logging.warning("%s is not a DICOM file !" % step_id)
    except IntegrityError:
        logging.warning("A problem occurred with the DB ! A rollback will be performed...")
        conn.db_session.rollback()


########################################################################################################################
# UTIL FUNCTIONS
########################################################################################################################

def format_date(date):
    try:
        return datetime.datetime(int(date[:4]), int(date[4:6]), int(date[6:8]))
    except ValueError:
        logging.warning("Cannot parse date from : "+str(date))


def format_gender(gender):
    if gender.lower() in MALE_GENDER_LIST:
        return MALE
    elif gender.lower() in FEMALE_GENDER_LIST:
        return FEMALE
    else:
        return DEFAULT_GENDER


def format_age(age):
    try:
        unit = age[3].upper()
        value = int(age[:3])
        if "Y" == unit:
            return float(value)
        elif "M" == unit:
            return float(value/12)
        elif "W" == unit:
            return float(value/52.1429)
        elif "D" == unit:
            return float(value/365)
        else:
            raise ValueError
    except ValueError:
        logging.warning("Cannot parse age from : "+str(age))


########################################################################################################################
# EXTRACTION FUNCTION
########################################################################################################################


def extract_participant(ds, handedness):
    try:
        participant_id = ds.PatientID
    except AttributeError:
        logging.warning("Patient ID was not found !")
        participant_id = DEFAULT_PARTICIPANT_ID
    try:
        participant_birth_date = format_date(ds.PatientBirthDate)
    except AttributeError:
        logging.debug("Field PatientBirthDate was not found")
        participant_birth_date = None
    try:
        participant_age = format_age(ds.PatientAge)
    except AttributeError:
        logging.debug("Field PatientAge was not found")
        participant_age = None
    try:
        participant_gender = format_gender(ds.PatientSex)
    except AttributeError:
        logging.debug("Field PatientSex was not found")
        participant_gender = DEFAULT_GENDER

    participant = conn.db_session.query(
        conn.Participant).filter_by(id=participant_id).first()

    if not participant:
        participant = conn.Participant(
            id=participant_id,
            gender=participant_gender,
            handedness=handedness,
            birthdate=participant_birth_date,
            age=participant_age
        )
        conn.db_session.add(participant)
        conn.db_session.commit()

    return participant.id


def extract_scan(ds, participant_id, role, comment):
    try:
        scan_date = format_date(ds.AcquisitionDate)
        if not scan_date:
            raise AttributeError
    except AttributeError:
        scan_date = format_date(ds.SeriesDate)  # If acquisition date is not available then we use the series date

    scan = conn.db_session.query(conn.Scan).filter_by(
        participant_id=participant_id, date=scan_date).first()

    if not scan:
        scan = conn.Scan(
            date=scan_date,
            role=role,
            comment=comment,
            participant_id=participant_id
        )
        conn.db_session.add(scan)
        conn.db_session.commit()

    return scan.id


def extract_session(ds, scan_id):
    try:
        session_value = str(ds.StudyID)
    except AttributeError:
        logging.debug("Field StudyID was not found")
        session_value = DEFAULT_SESSION_VALUE

    session = conn.db_session.query(conn.Session).filter_by(
        scan_id=scan_id, value=session_value).first()

    if not session:
        session = conn.Session(
            scan_id=scan_id,
            value=session_value
        )
        conn.db_session.add(session)
        conn.db_session.commit()

    return session.id


def extract_sequence_type(ds):
    try:
        sequence_name = ds.ProtocolName
    except AttributeError:
        logging.debug("Field ProtocolName was not found")
        sequence_name = 'unknown'
    try:
        manufacturer = ds.Manufacturer
    except AttributeError:
        logging.debug("Field Manufacturer was not found")
        manufacturer = 'unknown'
    try:
        manufacturer_model_name = ds.ManufacturerModelName
    except AttributeError:
        logging.debug("Field ManufacturerModelName was not found")
        manufacturer_model_name = 'unknown'
    try:
        institution_name = ds.InstitutionName
    except AttributeError:
        logging.debug("Field InstitutionName was not found")
        institution_name = 'unknown'
    try:
        slice_thickness = float(ds.SliceThickness)
    except (AttributeError, ValueError):
        logging.debug("Field SliceThickness was not found")
        slice_thickness = None
    try:
        repetition_time = float(ds.RepetitionTime)
    except (AttributeError, ValueError):
        logging.debug("Field RepetitionTime was not found")
        repetition_time = None
    try:
        echo_time = float(ds.EchoTime)
    except (AttributeError, ValueError):
        logging.debug("Field EchoTime was not found")
        echo_time = None
    try:
        number_of_phase_encoding_steps = int(ds.NumberOfPhaseEncodingSteps)
    except (AttributeError, ValueError):
        logging.debug("Field NumberOfPhaseEncodingSteps was not found")
        number_of_phase_encoding_steps = None
    try:
        percent_phase_field_of_view = float(ds.PercentPhaseFieldOfView)
    except (AttributeError, ValueError):
        logging.debug("Field PercentPhaseFieldOfView was not found")
        percent_phase_field_of_view = None
    try:
        pixel_bandwidth = int(ds.PixelBandwidth)
    except (AttributeError, ValueError):
        logging.debug("Field PixelBandwidth was not found")
        pixel_bandwidth = None
    try:
        flip_angle = float(ds.FlipAngle)
    except (AttributeError, ValueError):
        logging.debug("Field FlipAngle was not found")
        flip_angle = None
    try:
        rows = int(ds.Rows)
    except (AttributeError, ValueError):
        logging.debug("Field Rows was not found")
        rows = None
    try:
        columns = int(ds.Columns)
    except (AttributeError, ValueError):
        logging.debug("Field Columns was not found")
        columns = None
    try:
        magnetic_field_strength = float(ds.MagneticFieldStrength)
    except (AttributeError, ValueError):
        logging.debug("Field MagneticFieldStrength was not found")
        magnetic_field_strength = None
    try:
        echo_train_length = int(ds.EchoTrainLength)
    except (AttributeError, ValueError):
        logging.debug("Field EchoTrainLength was not found")
        echo_train_length = None
    try:
        percent_sampling = float(ds.PercentSampling)
    except (AttributeError, ValueError):
        logging.debug("Field PercentSampling was not found")
        percent_sampling = None
    try:
        pixel_spacing = ds.PixelSpacing
    except AttributeError:
        logging.debug("Field PixelSpacing was not found")
        pixel_spacing = None
    try:
        pixel_spacing_0 = float(pixel_spacing[0])
    except (AttributeError, ValueError, TypeError):
        logging.debug("Field pixel_spacing0 was not found")
        pixel_spacing_0 = None
    try:
        pixel_spacing_1 = float(pixel_spacing[1])
    except (AttributeError, ValueError, TypeError):
        logging.debug("Field pixel_spacing1 was not found")
        pixel_spacing_1 = None
    try:
        echo_number = int(ds.EchoNumber)
    except (AttributeError, ValueError):
        logging.debug("Field echo_number was not found")
        echo_number = None
    try:
        space_between_slices = float(ds[0x0018, 0x0088].value)
    except (AttributeError, ValueError, KeyError):
        logging.debug("Field space_between_slices was not found")
        space_between_slices = None

    sequence_type_list = conn.db_session.query(conn.SequenceType).filter_by(
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
        str(s.slice_thickness) != str(slice_thickness)
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
        sequence_type = conn.SequenceType(
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
        conn.db_session.add(sequence_type)
        conn.db_session.commit()

    return sequence_type.id


def extract_sequence(session_id, sequence_type_id):
    sequence = conn.db_session.query(conn.Sequence)\
        .filter_by(session_id=session_id, sequence_type_id=sequence_type_id)\
        .first()

    if not sequence:
        sequence = conn.Sequence(
            session_id=session_id,
            sequence_type_id=sequence_type_id
        )
        conn.db_session.add(sequence)
        conn.db_session.commit()

    return sequence.id


def extract_repetition(ds, sequence_id):
    try:
        repetition_value = int(ds.SeriesNumber)
    except AttributeError:
        logging.warning("Field SeriesNumber was not found")
        repetition_value = DEFAULT_REPETITION

    repetition = conn.db_session.query(conn.Repetition).filter_by(
        sequence_id=sequence_id, value=repetition_value).first()

    if not repetition:
        repetition = conn.Repetition(
            sequence_id=sequence_id,
            value=repetition_value
        )
        conn.db_session.add(repetition)
        conn.db_session.commit()

    return repetition.id


def extract_dicom(path, file_type, is_copy, repetition_id, processing_step_id):
    dcm = conn.db_session.query(conn.DataFile).filter_by(
        path=path, repetition_id=repetition_id).first()

    if not dcm:
        dcm = conn.DataFile(
            path=path,
            type=file_type,
            repetition_id=repetition_id,
            processing_step_id=processing_step_id,
            is_copy=is_copy
        )
        conn.db_session.add(dcm)
        conn.db_session.commit()

    return dcm.id
