# coding: utf-8
from sqlalchemy import Column, Date, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()
metadata = Base.metadata


class Check(Base):
    __tablename__ = 'check'

    id = Column(Integer, primary_key=True, nullable=False)
    quality_check_id = Column(ForeignKey('quality_check.id'), primary_key=True, nullable=False, index=True)
    nifti_id = Column(ForeignKey('nifti.id'), primary_key=True, nullable=False, index=True)
    value = Column(Float, nullable=False)

    nifti = relationship('Nifti')
    quality_check = relationship('QualityCheck')


class Dicom(Base):
    __tablename__ = 'dicom'

    id = Column(Integer, primary_key=True, nullable=False)
    repetition_id = Column(ForeignKey('repetition.id'), primary_key=True, nullable=False, index=True)
    path = Column(Text, nullable=False)

    repetition = relationship('Repetition')


class Nifti(Base):
    __tablename__ = 'nifti'

    id = Column(Integer, primary_key=True, nullable=False)
    repetition_id = Column(ForeignKey('repetition.id'), primary_key=True, nullable=False, index=True)
    path = Column(Text, nullable=False)
    result_type = Column(String(255), nullable=False)
    output_type = Column(String(255), nullable=False)

    repetition = relationship('Repetition')


class Participant(Base):
    __tablename__ = 'participant'

    id = Column(String(255), primary_key=True)
    gender = Column(Enum('male', 'female', 'other', 'unknown'), nullable=False)
    handedness = Column(Enum('left', 'right', 'ambidexter', 'unknown'), nullable=False)
    birthdate = Column(Date, nullable=False)


class Project(Base):
    __tablename__ = 'project'

    id = Column(Integer, primary_key=True)
    researcher_id = Column(ForeignKey('researcher.id'), nullable=False, index=True)
    scan_id = Column(ForeignKey('scan.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False, unique=True)

    researcher = relationship('Researcher')
    scan = relationship('Scan')


class QualityCheck(Base):
    __tablename__ = 'quality_check'

    id = Column(Integer, primary_key=True, nullable=False)
    scientist_id = Column(ForeignKey('researcher.id'), primary_key=True, nullable=False, index=True)

    scientist = relationship('Researcher')


class Repetition(Base):
    __tablename__ = 'repetition'

    id = Column(Integer, primary_key=True, nullable=False)
    sequence_id = Column(ForeignKey('sequence.id'), primary_key=True, nullable=False, index=True)
    value = Column(Integer, nullable=False)

    sequence = relationship('Sequence')


class Researcher(Base):
    __tablename__ = 'researcher'

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String(255), primary_key=True, nullable=False)
    firstname = Column(String(255), nullable=False)
    lastname = Column(String(255), nullable=False)


class Responsible(Base):
    __tablename__ = 'responsible'

    scientist_id = Column(ForeignKey('researcher.id'), primary_key=True, nullable=False, index=True)
    scan_id = Column(ForeignKey('scan.id'), primary_key=True, nullable=False, index=True)
    role = Column(Enum('technician', 'supervisor'), nullable=False)

    scan = relationship('Scan')
    scientist = relationship('Researcher')


class Scan(Base):
    __tablename__ = 'scan'

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    role = Column(Enum('C', 'P', 'IC', 'U'), nullable=False)
    comment = Column(Text, nullable=False)
    participant_id = Column(ForeignKey('participant.id'), nullable=False, index=True)

    participant = relationship('Participant')


class Sequence(Base):
    __tablename__ = 'sequence'

    id = Column(Integer, primary_key=True, nullable=False)
    session_id = Column(ForeignKey('session.id'), primary_key=True, nullable=False, index=True)
    sequence_type_id = Column(ForeignKey('sequence_type.id'), primary_key=True, nullable=False, index=True)

    sequence_type = relationship('SequenceType')
    session = relationship('Session')


class SequenceType(Base):
    __tablename__ = 'sequence_type'

    id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False)
    manufacturer = Column(String(45), nullable=False)
    manufacturer_model_name = Column(String(45), nullable=False)
    institution_name = Column(String(45), nullable=False)
    slice_thickness = Column(Float, nullable=False)
    repetition_time = Column(Float, nullable=False)
    echo_time = Column(Float, nullable=False)
    echo_number = Column(Integer, nullable=False)
    number_of_phase_encoding_steps = Column(Integer, nullable=False)
    percent_phase_field_of_view = Column(Float, nullable=False)
    pixel_bandwidth = Column(Integer, nullable=False)
    flip_angle = Column(Float, nullable=False)
    rows = Column(Integer, nullable=False)
    columns = Column(Integer, nullable=False)
    magnetic_field_strength = Column(Float, nullable=False)
    space_between_slices = Column(Float, nullable=False)
    echo_train_length = Column(Integer, nullable=False)
    percent_sampling = Column(Float, nullable=False)
    pixel_spacing_0 = Column(Float, nullable=False)
    pixel_spacing_1 = Column(Float, nullable=False)


class Session(Base):
    __tablename__ = 'session'

    id = Column(Integer, primary_key=True, nullable=False)
    scan_id = Column(ForeignKey('scan.id'), primary_key=True, nullable=False, index=True)
    value = Column(Integer, nullable=False)

    scan = relationship('Scan')
