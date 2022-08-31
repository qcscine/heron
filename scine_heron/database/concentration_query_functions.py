#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""

from typing import List, Union

# Third party imports
import scine_database as db


def query_concentration(label: str, centroid: db.Structure, properties: db.Collection) -> float:
    """
    Query a concentration for a given structure.

    Parameters
    ----------
    label : str
        The concentration property label.
    centroid : db.Structure
        The structure as a linked object.
    properties : db.Collection
        The property collection.

    Returns
    -------
    float
        The concentration according to property label. Return 0.0 if no property is present.
    """
    property_list = centroid.get_properties(label)
    if not property_list:
        return 0.0
    # pick last property if multiple
    prop = db.NumberProperty(property_list[-1], properties)
    return prop.get_data()


def query_concentration_list(label: str, centroid: db.Structure, properties: db.Collection) -> List[float]:
    """
    Query all concentrations of a given type for a structure.

    Parameters
    ----------
    label : str
        The concentration property label.
    centroid : db.Structure
        The structure as a linked object.
    properties : db.Collection
        The property collection.

    Returns
    -------
    List[float]
        The concentrations according to property label. Returns an empty list if no property is present.
    """
    property_list = centroid.get_properties(label)
    concentrations = list()
    for generic_property in property_list:
        prop = db.NumberProperty(generic_property, properties)
        concentrations.append(prop.get_data())
    return concentrations


def query_reaction_flux(label_post_fix: str, reaction: db.Reaction, compounds: db.Collection, flasks: db.Collection,
                        structures: db.Collection, properties: db.Collection):
    """
    Query the concentration flux for a given reaction.

    Parameters
    ----------
    label_post_fix :: str
        The property label for the concentration flux will be given as reaction.id().string() + label_post_fix
    reaction : db.Reaction
        The reaction.
    compounds : db.Collection
        The compound collection.
    flasks : db.Collection
        The flask collection.
    structures : db.Collection
        The structure collection.
    properties : db.Collection
        The property collection.

    Returns
    -------
    float
        The concentration flux along the reaction. If no flux is given in the database, 0.0 is returned.
    """
    label = reaction.id().string() + label_post_fix
    a_id = reaction.get_reactants(db.Side.LHS)[0][0]
    a_type = reaction.get_reactant_types(db.Side.LHS)[0][0]
    if a_type == db.CompoundOrFlask.FLASK:
        aggregate: Union[db.Compound, db.Flask] = db.Flask(a_id, flasks)
    else:
        assert a_type == db.CompoundOrFlask.COMPOUND
        aggregate = db.Compound(a_id, compounds)
    structure = db.Structure(aggregate.get_centroid(), structures)
    return query_concentration(label, structure, properties)
