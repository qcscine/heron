#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from scine_art.database import ReactionTemplateDatabase
from scine_art.reaction_template import ReactionTemplate

from typing import TYPE_CHECKING, Any, List, Optional
from PySide2.QtCore import QObject
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


class ReactionTemplateStorage(QObject):

    reaction_template_count_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.__template_db = ReactionTemplateDatabase()
        self.__template_ids: List[str] = []

    def add_reaction_template(self, new_template: ReactionTemplate) -> None:
        new_id = self.__template_db.add_template(new_template)
        if new_id not in self.__template_ids:
            self.__template_ids.append(new_id)
            self.reaction_template_count_changed.emit(self.__template_db.template_count())
        assert self.__template_db.template_count() == len(self.__template_ids)

    def clear(self):
        self.__template_db = ReactionTemplateDatabase()
        self.__template_ids = []
        assert self.__template_db.template_count() == len(self.__template_ids)
        self.reaction_template_count_changed.emit(self.__template_db.template_count())

    def load_database(self, filename: str) -> None:
        self.clear()
        self.add_database(filename)

    def add_database(self, filename: str) -> None:
        self.__template_db.append_file(filename)
        self.__template_ids = []
        for rt in self.__template_db.iterate_templates():
            self.__template_ids.append(rt.get_uuid())
        self.reaction_template_count_changed.emit(self.__template_db.template_count())

    def save_database(self, filename: str) -> None:
        self.__template_db.save(filename)

    def get_template_ids(self) -> List[str]:
        return self.__template_ids

    def get_template(self, rt_id: str) -> Optional[ReactionTemplate]:
        return self.__template_db.get_template(rt_id)
