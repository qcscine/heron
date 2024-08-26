#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Any


class DummyType(type):
    def __getattribute__(self, item):
        if item.startswith("__"):
            return super().__getattribute__(item)
        return super().__new__(DummyType, "DummyType", (type,), globals())


class DummyClass(metaclass=DummyType):

    def __init__(self, *args, **kwargs):
        self.cls = None

    def __getattribute__(self, item):
        if item == "__class__":
            return object.__getattribute__(self, "__class__")
        try:
            return object.__getattribute__(self, "cls")
        except AttributeError:
            return object.__getattribute__(self, "__class__")

    def __setattr__(self, key, value):
        pass

    def __getitem__(self, item):
        return getattr(self, "cls")

    def __setitem__(self, key, value):
        pass

    def __call__(self, *args, **kwargs):
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}()"


class NotMatchingClass(DummyClass):
    """
    This class is returned as a placeholder for any demanded module/class
    that is an optional dependency and is not installed.
    Its main task is to not match any types in type checks.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cls = self.__class__


class AnyMatchingClass(DummyClass):
    """
    Same idea as NotMatchClass, but with the idea to match every type check.
    However, any returned variables did work as typehints for mypy, so currently unused.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cls = Any
