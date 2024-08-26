#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from inspect import signature
from typing import Type, Any, Union

from scine_chemoton.gears import Gear
from scine_chemoton.gears.kinetic_modeling.kinetic_modeling import KineticModeling
from scine_chemoton.gears.network_refinement.calculation_based_refinement import CalculationBasedRefinement
from scine_chemoton.filters.aggregate_filters import AggregateFilter
from scine_chemoton.filters.reactive_site_filters import ReactiveSiteFilter
from scine_chemoton.filters.further_exploration_filters import FurtherExplorationFilter
from scine_chemoton.filters.reaction_filters import ReactionFilter
from scine_chemoton.filters.elementary_step_filters import ElementaryStepFilter
from scine_chemoton.filters.structure_filters import StructureFilter
from scine_chemoton.utilities.datastructure_transfer import make_picklable
from scine_chemoton.utilities.reactive_complexes.lebedev_sphere import LebedevSphere

from scine_heron.chemoton.class_searcher import ChemotonClassSearcher
from scine_heron.settings.docstring_parser import DocStringParser
from scine_heron.io.json_pickle_wrap import encode, decode


def attribute_comparison(obj1, obj2) -> bool:
    """
    Compares the attributes of two objects.
    """
    if obj1.__class__ != obj2.__class__:
        return False
    if isinstance(obj1, CalculationBasedRefinement.Options) and isinstance(obj2, CalculationBasedRefinement.Options):
        return True
    attr1 = {k: getattr(obj1, k) for k in dir(obj1) if not k.startswith("__") and not callable(getattr(obj1, k))}
    attr2 = {k: getattr(obj2, k) for k in dir(obj2) if not k.startswith("__") and not callable(getattr(obj2, k))}
    if len(attr1) != len(attr2):
        return False
    for k1, v1 in attr1.items():
        if k1 not in attr2:
            return False
        v2 = attr2[k1]
        if isinstance(v1, LebedevSphere) and isinstance(v2, LebedevSphere):
            continue
        try:
            if v1 != v2 and not attribute_comparison(v1, v2):
                return False
        except BaseException:
            if not attribute_comparison(v1, v2):
                return False
    return True


def generate_class_with_all_default_constructors(param_type: Type) -> Any:
    if param_type in [float, str, int, bool]:
        return param_type()
    while getattr(param_type, "__origin__", None) is Union:
        # If the type is a Union, we take the first type
        param_type = param_type.__args__[0]
    if hasattr(param_type, "__origin__"):
        param_type = getattr(param_type, "__origin__")
        init_arg_list = getattr(param_type, "__args__", [])
        return param_type(*[generate_class_with_all_default_constructors(t) for t in init_arg_list])

    try:
        sig = signature(param_type)
    except ValueError:
        try:
            return param_type()
        except (TypeError, ValueError) as e:
            raise ValueError from e

    init_args = {}
    for name, param in sig.parameters.items():
        # Generate mock data for each parameter
        init_args[name] = generate_class_with_all_default_constructors(param.annotation)
    if not init_args:
        return param_type()
    try:
        return param_type(**init_args)
    except BaseException:
        try:
            return param_type(*init_args.values())
        except BaseException as e:
            raise ValueError from e


def test_gears_encoding():
    parser = DocStringParser()
    searcher = ChemotonClassSearcher(Gear)
    for gear_cls in searcher.values():
        gear = gear_cls()
        parser.get_docstring_for_object_attrs(gear_cls.__name__, gear.options)
        gear_dict = encode(make_picklable(gear))
        new_gear = decode(gear_dict)
        assert attribute_comparison(gear, new_gear)
        if not isinstance(gear, KineticModeling) and not isinstance(gear, CalculationBasedRefinement):
            # mmb
            assert gear.options == new_gear.options


def test_filters_encoding():
    parser = DocStringParser()
    for filter_type in [AggregateFilter,
                        ReactiveSiteFilter,
                        FurtherExplorationFilter,
                        ReactionFilter,
                        ElementaryStepFilter,
                        StructureFilter]:
        searcher = ChemotonClassSearcher(filter_type)
        for filter_cls in searcher.values():

            # Generate arguments based on the signature
            try:
                filter_ = generate_class_with_all_default_constructors(filter_cls)
            except ValueError:
                # some filter require correct arguments that cannot be deduced
                # such as a path to a file
                continue
            parser.get_docstring_for_class_init(filter_cls.__name__, filter_)
            filter_dict = encode(make_picklable(filter_))
            new_filter = decode(filter_dict)
            assert attribute_comparison(filter_, new_filter)
