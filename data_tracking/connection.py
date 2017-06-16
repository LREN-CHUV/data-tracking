from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import orm
from sqlalchemy.sql import functions as sql_func

from airflow import configuration


class Connection:

    def __init__(self, db_url=None):
        if db_url is None:
            db_url = configuration.get('data-factory', 'DATA_CATALOG_SQL_ALCHEMY_CONN')

        self.Base = automap_base()
        self.engine = create_engine(db_url)
        self.Base.prepare(self.engine, reflect=True)

        self.ParticipantMapping = self.Base.classes.participant_mapping
        self.Participant = self.Base.classes.participant
        self.Visit = self.Base.classes.visit
        self.VisitMapping = self.Base.classes.visit_mapping
        self.DataFile = self.Base.classes.data_file
        self.Session = self.Base.classes.session
        self.SequenceType = self.Base.classes.sequence_type
        self.Sequence = self.Base.classes.sequence
        self.Repetition = self.Base.classes.repetition
        self.ProcessingStep = self.Base.classes.processing_step
        self.Provenance = self.Base.classes.provenance

        self.db_session = orm.Session(self.engine)

    def close(self):
        self.db_session.close()

    def get_dataset(self, step_id):
        provenance_id = self.db_session.query(self.ProcessingStep).filter_by(id=step_id).first().provenance_id
        return self.db_session.query(self.Provenance).filter_by(id=provenance_id).first().dataset

    def new_participant_id(self):
        try:
            return self.db_session.query(
                sql_func.max(self.ParticipantMapping.participant_id).label('max')).one().max + 1
        except TypeError:
            return 0

    def get_participant_id(self, participant_name, dataset):
        participant_name = str(participant_name)
        participant = self.db_session.query(self.ParticipantMapping).filter_by(
            dataset=dataset, name=participant_name).one_or_none()
        if not participant:
            participant = self.ParticipantMapping(dataset=dataset, name=participant_name,
                                                  participant_id=self.new_participant_id())
            self.db_session.merge(participant)
            self.db_session.commit()
        return self.db_session.query(self.ParticipantMapping).filter_by(
            dataset=dataset, name=participant_name).one_or_none().participant_id

    def new_visit_id(self):
        try:
            return self.db_session.query(
                sql_func.max(self.VisitMapping.visit_id).label('max')).one().max + 1
        except TypeError:
            return 0

    def get_visit_id(self, visit_name, dataset):
        visit_name = str(visit_name)
        visit = self.db_session.query(self.VisitMapping).filter_by(
            dataset=dataset, name=visit_name).one_or_none()
        if not visit:
            visit = self.VisitMapping(dataset=dataset, name=visit_name, visit_id=self.new_visit_id())
            self.db_session.merge(visit)
            self.db_session.commit()
        return self.db_session.query(self.VisitMapping).filter_by(
            dataset=dataset, name=visit_name).one_or_none().visit_id

    def get_session_id(self, session_name, visit_id):
        session_name = str(session_name)
        session = self.db_session.query(self.Session).filter_by(
            name=session_name, visit_id=visit_id).one_or_none()
        if not session:
            session = self.Session(name=session_name, visit_id=visit_id)
            self.db_session.merge(session)
            self.db_session.commit()
        return self.db_session.query(self.Session).filter_by(
            name=session_name, visit_id=visit_id).one_or_none().id

    def get_sequence_id(self, sequence_name, session_id):
        sequence_name = str(sequence_name)
        sequence = self.db_session.query(self.Sequence).filter_by(
            name=sequence_name, session_id=session_id).one_or_none()
        if not sequence:
            sequence = self.Sequence(name=sequence_name, session_id=session_id)
            self.db_session.merge(sequence)
            self.db_session.commit()
        return self.db_session.query(self.Sequence).filter_by(
            name=sequence_name, session_id=session_id).one_or_none().id

    def get_repetition_id(self, repetition_name, sequence_id):
        repetition_name = str(repetition_name)
        repetition = self.db_session.query(self.Repetition).filter_by(
            name=repetition_name, sequence_id=sequence_id).one_or_none()
        if not repetition:
            repetition = self.Repetition(name=repetition_name, sequence_id=sequence_id)
            self.db_session.merge(repetition)
            self.db_session.commit()
        return self.db_session.query(self.Repetition).filter_by(
            name=repetition_name, sequence_id=sequence_id).one_or_none().id
