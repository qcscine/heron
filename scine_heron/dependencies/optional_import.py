#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from inspect import isfunction
from typing import Any, Optional
import importlib

from .dummy import AnyMatchingClass, NotMatchingClass, DummyClass


def importer(module: str, attr: Optional[str] = None, return_any: bool = False):
    """
    This function is used to import optional dependencies.

    Parameters
    ----------
    module : str
        The module to import given as 'scine_heron.dependencies.optional_import'.
    attr : str, optional
        The attribute to import from the module, e.g. 'importer'.
    return_any : bool, optional
        If True, the function will return AnyMatchingClass instead of NotMatchingClass if the dependency is not
        installed.

    Returns
    -------
    result : Any
    """
    try:
        if attr is not None:
            return getattr(importlib.import_module(module), attr)
        return importlib.import_module(module)
    except (ImportError, AttributeError):
        return AnyMatchingClass if return_any else NotMatchingClass


def is_imported(obj: Any) -> bool:
    """
    Checks if the given object is a dummy object or a proper instance, type, or function.

    Returns True if the object is not a dummy object, False otherwise.
    """
    if isfunction(obj):
        return True
    try:
        return not issubclass(obj, DummyClass)
    except TypeError:
        return not isinstance(obj, DummyClass)
