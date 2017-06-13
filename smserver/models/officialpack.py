#!/usr/bin/env python3
# -*- coding: utf8 -*-

import datetime

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from smserver.models import schema

__all__ = ['OfficialPack']

class OfficialPack(schema.Base):
    __tablename__ = 'officialpacks'

    id           = Column(Integer, primary_key=True)
    url        = Column(String(128))
    packid        = Column(Integer, ForeignKey('packs.id'))
    size        = Column(Integer) #mb

    pack = relationship("Pack", back_populates="officialpack")

    def __repr__(self):
        return "<OfficialPack #%s (url='%s', packid='%s')>" % (self.id, self.url, self.packid)

    @classmethod
    def find_or_create(cls, url, packid, session):
        officialpack = session.query(cls).filter_by(url=url).filter_by(packid=packid).first()
        if not pack:
            officialpack = cls(url=url, packid=packid)
            session.add(pack)
            session.commit()

        return officialpack
