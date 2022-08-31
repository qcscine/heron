#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the DocStringParser class.
"""

import ast
import inspect
from itertools import tee
from typing import Dict, Tuple, Union, Any, Iterator


class DocStringParser:
    """
    Automatically parse Attribute Docstrings.
    """

    def __init__(self) -> None:
        self.__cache: Dict[str, Dict[str, str]] = {}

    def get_docstring_for_object_attrs(self, name: str, o: object) -> Dict[str, str]:
        """
        Extracts PEP-224 docstrings for variables of `o`.
        """
        if name in self.__cache:
            return self.__cache[name]

        data: Dict[str, str] = dict()

        lines, _ = inspect.getsourcelines(o.__class__)
        doc = inspect.cleandoc("".join(["\n"] + lines))
        tree = ast.parse(doc).body[0]

        for node in reversed(tree.body):  # type: ignore[attr-defined]
            if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                for assign_node, str_node in self.__pairwise(
                    ast.iter_child_nodes(node)
                ):
                    if not (
                        isinstance(assign_node, (ast.Assign, ast.AnnAssign))
                        and isinstance(str_node, ast.Expr)
                        and isinstance(str_node.value, ast.Str)
                    ):
                        continue
                    docstring = inspect.cleandoc(str_node.value.s).strip()
                    data[self.__get_name(assign_node)] = docstring

        self.__cache[name] = data

        return data

    @staticmethod
    def __pairwise(iterable: Iterator[Any]) -> Iterator[Tuple[Any, Any]]:
        """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)

    @staticmethod
    def __get_name(assign: Union[ast.Assign, ast.AnnAssign]) -> Any:
        if isinstance(assign, ast.Assign) and len(assign.targets) == 1:
            target = assign.targets[0]
        elif isinstance(assign, ast.AnnAssign):
            target = assign.target
        else:
            return str()
        return target.attr  # type: ignore[attr-defined]
