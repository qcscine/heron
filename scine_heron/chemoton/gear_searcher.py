#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the GearSearcher class.
"""

import re
import os
import ast
import _ast
import importlib
from scine_chemoton import gears  # pylint: disable=import-error
from typing import List, Tuple, Dict, Any


class GearSearcher:
    """
    Automatically gather a list of all possible Gears from scine_chemoton.
    """

    def __init__(self) -> None:
        """
        Search for all subclasses of gears.Gear in scine_chemoton and save them in self.gears.
        Key in self.gears is a class name and value is a class type.
        """
        self.gears: Dict[str, Any] = dict()
        self.module_to_class: Dict[str, List[str]] = dict()

        for path, class_name in GearSearcher.__get_all_classes_names_from_chemoton():
            module = importlib.import_module(path)
            module_name = module.__name__.replace("scine_chemoton.gears.", "")
            loaded_class = getattr(module, class_name)

            if issubclass(loaded_class, gears.Gear):
                if class_name == "Gear" and path == "scine_chemoton.gears":
                    # skip base class
                    continue

                human_readable_name = self.__human_readable_gear_names(class_name)
                self.gears[human_readable_name] = loaded_class

                if module_name not in self.module_to_class:
                    self.module_to_class[module_name] = []
                self.module_to_class[module_name].append(human_readable_name)

    @staticmethod
    def __human_readable_gear_names(gear_name: str) -> str:
        # Split a string at uppercase letters
        words = [s for s in re.split("([A-Z][^A-Z]*)", gear_name) if s]

        # convert all words except the first to lowercase
        for i in range(1, len(words)):
            words[i] = words[i].capitalize()

        # join with space
        return " ".join(words)

    @staticmethod
    def __get_all_classes_names_from_chemoton() -> List[Tuple[str, str]]:
        """
        Search for all classes in scine_chemoton.gears module.
        Returns a list of Tuples of module path and class name.
        """
        classes = []
        for path in GearSearcher.__get_files_names_from_chemoton():
            with open(path) as mf:
                tree = ast.parse(mf.read())

            # parse module path
            module_path = path.split("scine_chemoton")[1]
            module_path = module_path.replace(".py", "")
            module_path = module_path.replace("/__init__", "")
            module_path = "scine_chemoton" + module_path.replace("/", ".")

            # parse classes names
            module_classes = [_ for _ in tree.body if isinstance(_, _ast.ClassDef)]
            classes.extend([(module_path, c.name) for c in module_classes])
        return classes

    @staticmethod
    def __get_files_names_from_chemoton() -> List[str]:
        """
        Search for all .py files in scine_chemoton.gears module.
        """
        path = os.path.dirname(gears.__file__)

        py_files = []

        for root, _, files in os.walk(path):
            for file in files:
                if ".py" in file and ".pyc" not in file:
                    py_files.append(os.path.join(root, file))

        return py_files
