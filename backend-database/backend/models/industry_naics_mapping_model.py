from .lead_model import db
from sqlalchemy import Column, Integer, String

class IndustryNAICSMappings(db.Model):
    __tablename__ = 'industry_naics_mapping'

    id = Column('ID', Integer, primary_key=True)
    exact_industry = Column('Exact_Industry', String(255))
    corrected_industry = Column('Corrected_Industry', String(255))
    similar_naics_industry_name = Column('Similar_NAICS_Industry_Name', String(255))
    parent_naics_industry_name = Column('Parent_NAICS_Industry_Name', String(255))
    similar_naics_industry_code = Column('Similar_NAICS_Industry_Code', String(10))
    parent_naics_industry_code = Column('Parent_NAICS_Industry_Code', String(2))

    def to_dict(self):
        return {
            'id': self.id,
            'exact_industry': self.exact_industry,
            'corrected_industry': self.corrected_industry,
            'similar_naics_industry_name': self.similar_naics_industry_name,
            'parent_naics_industry_name': self.parent_naics_industry_name,
            'similar_naics_industry_code': self.similar_naics_industry_code,
            'parent_naics_industry_code': self.parent_naics_industry_code,
        }