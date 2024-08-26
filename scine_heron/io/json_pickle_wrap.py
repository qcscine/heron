#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
This module provides two functions of jsonpickle with hardcoded defaults and
it ensures that we serialize all our own classes correctly as soon as this module is loaded.
jsonpickle allows to safe an object in an human-readable format.
"""


from enum import Enum
from typing import Any, TYPE_CHECKING
import jsonpickle
import jsonpickle.ext.numpy as jsonpickle_numpy

from scine_utilities import ElementInfo, ElementType, AtomCollection

from scine_heron.dependencies.optional_import import importer, is_imported

if TYPE_CHECKING:
    from scine_chemoton.steering_wheel.datastructures import Status, LogicCoupling
    from scine_chemoton.utilities.reactive_complexes.lebedev_sphere import LebedevSphere
    from scine_database import Label
    from scine_chemoton.utilities.place_holder_model import PlaceHolderModelType, _PlaceHolderModelProxy
else:
    Status = importer("scine_chemoton.steering_wheel.datastructures", "Status")
    LogicCoupling = importer("scine_chemoton.steering_wheel.datastructures", "LogicCoupling")
    LebedevSphere = importer("scine_chemoton.utilities.reactive_complexes.lebedev_sphere", "LebedevSphere")
    Label = importer("scine_database", "Label")
    PlaceHolderModelType = importer("scine_chemoton.utilities.place_holder_model", "PlaceHolderModelType")
    _PlaceHolderModelProxy = importer("scine_chemoton.utilities.place_holder_model", "_PlaceHolderModelProxy")


class EnumHandler(jsonpickle.handlers.BaseHandler):
    """
    This handler exists because jsonpickle has problems with our Enum derived classes.
    """

    def flatten(self, obj, data):
        data['value'] = self.context.flatten(repr(obj), reset=False)
        return data

    def restore(self, obj):
        return self.context.restore(eval(obj['value'].split("<")[-1].split(":")[0]),  # pylint: disable=eval-used
                                    reset=False)


class ProxyHandler(jsonpickle.handlers.BaseHandler):
    """
    This class circumvents jsonpickle's problem with Proxy objects
    """
    _proxy = _PlaceHolderModelProxy

    def flatten(self, obj, data):
        data['state'] = self.context.flatten(obj.__getstate__(), reset=False)
        return data

    def restore(self, obj):
        proxy = self._proxy()
        proxy.__setstate__(obj['state'])
        return self.context.restore(proxy,
                                    reset=False)


class SimpleReprEvalHandler(jsonpickle.handlers.BaseHandler):
    """
    This handler offers an easy implementation for all classes that work with an
    eval(repr(inst)) call.
    """

    def flatten(self, obj, data):
        data['value'] = self.context.flatten(repr(obj), reset=False)
        return data

    def restore(self, obj):
        return self.context.restore(eval(obj['value']),  # pylint: disable=eval-used
                                    reset=False)


class ElementHandler(jsonpickle.handlers.BaseHandler):
    """
    This handler stores Scine Utilities ElementTypes by their string representation.
    To be removed once pickling support is available from Scine Utilities.
    """

    def flatten(self, obj, data):
        data['value'] = self.context.flatten(str(obj), reset=False)
        return data

    def restore(self, obj):
        return self.context.restore(ElementInfo.element_from_symbol(obj['value']), reset=False)


class AtomCollectionHandler(jsonpickle_numpy.NumpyGenericHandler):
    """
    This handler stores Scine AtomCollections by saving elements and positions separately.
    It inherits from NumpyGenericHandler to store the positions as numpy arrays.
    """

    def flatten(self, obj, data):
        pos_data = {}
        data['positions'] = super().flatten(obj.positions, pos_data)
        data['elements'] = self.context.flatten(repr([str(e) for e in obj.elements]), reset=False)
        return data

    def restore(self, data):
        elements = self.context.restore([ElementInfo.element_from_symbol(e)
                                         for e in eval(data['elements'])],  # pylint: disable=eval-used
                                        reset=False)
        positions = super().restore(data['positions'])
        return AtomCollection(elements, positions)


def encode(obj: Any) -> str:
    """
    A wrap with default parameters for jsonpickle.encode.

    Parameters
    ----------
    obj : Any
        The object to encode

    Returns
    -------
    str
        The encoded object as a string
    """
    return jsonpickle.encode(obj,
                             keys=True,  # otherwise non-string keys will fail
                             unpicklable=True,  # just to be sure in case of future changes
                             make_refs=False,  # python ids are not preserved
                             warn=True,  # warn about unpicklable objects, safer development for now
                             max_iter=-1,  # no limit
                             indent=2,  # pretty print
                             separators=(",", ": "),  # pretty print
                             include_properties=False,  # can fail for class attributes
                             )


def decode(obj: str) -> Any:
    """
    A wrap with default parameters for jsonpickle.decode

    Parameters
    ----------
    obj : str
        The encoded object as a string

    Returns
    -------
    Any
        The decoded object
    """
    return jsonpickle.decode(obj,
                             keys=True,  # otherwise non-string keys will fail
                             on_missing='error')


# register all Handlers automatically when this module is imported
EnumHandler.handles(Enum)
# have to register all enum derived classes separate
if is_imported(Status):
    EnumHandler.handles(Status)
if is_imported(LogicCoupling):
    EnumHandler.handles(LogicCoupling)
if is_imported(Label):
    EnumHandler.handles(Label)
if is_imported(LebedevSphere):
    SimpleReprEvalHandler.handles(LebedevSphere)
if is_imported(PlaceHolderModelType):
    ProxyHandler.handles(PlaceHolderModelType)
ElementHandler.handles(ElementType)
AtomCollectionHandler.handles(AtomCollection)
jsonpickle_numpy.register_handlers()  # numpy objects
