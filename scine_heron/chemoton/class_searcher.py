#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the ChemotonClassSearcher class.
"""

import re
import os
import ast
import _ast
import importlib
from collections import UserDict
from inspect import isabstract, getmembers
from typing import List, Tuple, Dict, Type, Optional

import scine_chemoton


class ChemotonClassSearcher(UserDict):
    """
    Automatically gather a list of all possible classes from scine_chemoton that are a subclass of the given type
    """

    def __init__(self, class_to_search: Type, black_list: Optional[List[Type]] = None,
                 avoid_exact_match: bool = False) -> None:
        """
        Search for all subclasses of given class in scine_chemoton and save them in this object.
        Key is a class name and value is a class type.
        """
        super().__init__()
        self.search_type: Type = class_to_search
        self.module_to_class: Dict[str, List[str]] = dict()

        for path, class_name in ChemotonClassSearcher.__get_all_classes_names_from_chemoton():
            module = importlib.import_module(path)
            module_name = module.__name__.replace("scine_chemoton.", "")
            module_name_split = module_name.split(".")
            # cut away first submodule
            if len(module_name_split) > 1:
                module_name = ".".join(module_name_split[1:])
            loaded_class = getattr(module, class_name)

            if avoid_exact_match and loaded_class == class_to_search:
                continue

            if issubclass(loaded_class, class_to_search):
                if isabstract(loaded_class):
                    continue
                if black_list is not None:
                    if any(issubclass(loaded_class, b) for b in black_list):
                        continue

                human_readable_name = self.__human_readable_class_names(class_name)
                self.data[human_readable_name] = loaded_class

                if module_name not in self.module_to_class:
                    self.module_to_class[module_name] = []
                self.module_to_class[module_name].append(human_readable_name)

    @staticmethod
    def __human_readable_class_names(class_name: str) -> str:
        # Split a string at uppercase letters
        words = [s for s in re.split("([A-Z][^A-Z]*)", class_name) if s]

        # convert all words except the first to lowercase
        for i in range(1, len(words)):
            words[i] = words[i].capitalize()

        # join with space
        return " ".join(words)

    @staticmethod
    def __get_all_classes_names_from_chemoton() -> List[Tuple[str, str]]:
        """
        Search for all classes in scine_chemoton module.
        Returns a list of Tuples of module path and class name.
        """
        classes = []
        for path in ChemotonClassSearcher.__get_files_names_from_chemoton():
            with open(path) as mf:
                tree = ast.parse(mf.read())

            # parse module path
            module_path = path.split("scine_chemoton")[-1]
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
        Return all .py files in scine_chemoton module.
        """
        location = None
        try:
            location = scine_chemoton.__file__  # can also be None
        except AttributeError:
            pass
        if location is None:
            members = getmembers(scine_chemoton)
            for m in members:
                if "__file__" in m and m[1] is not None:
                    location = m[1]
                    break
                if "__path__" in m and m[1] is not None:
                    for possible_location in m[1]:
                        if os.path.exists(possible_location):
                            location = possible_location
                            break
            if location is None:
                raise RuntimeError("The location of your installed SCINE Chemoton could not be determined")
        path = os.path.dirname(location)

        py_files = []

        for root, _, files in os.walk(path):
            for f in files:
                if f[-3:] == ".py":
                    py_files.append(os.path.join(root, f))

        return py_files
