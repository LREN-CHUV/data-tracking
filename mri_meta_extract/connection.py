from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import orm
from sqlalchemy.sql import functions as sql_func

from airflow import configuration


class Connection:

    def __init__(self, db_url=None):
        if db_url is None:
            db_url = configuration.get('mri', 'SQL_ALCHEMY_CONN')

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
            self.db_session.add(participant)
            self.db_session.commit()
        return participant.participant_id

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
            self.db_session.add(visit)
            self.db_session.commit()
        return visit.visit_id
