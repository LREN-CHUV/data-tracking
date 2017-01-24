from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import orm

from airflow import configuration


class Connection:

    def __init__(self, db_url=None):
        if db_url is None:
            db_url = configuration.get('mri', 'SQL_ALCHEMY_CONN')

        self.Base = automap_base()
        self.engine = create_engine(db_url)
        self.Base.prepare(self.engine, reflect=True)

        self.Participant = self.Base.classes.participant
        self.Scan = self.Base.classes.scan
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
