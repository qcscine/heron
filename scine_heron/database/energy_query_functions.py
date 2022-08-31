#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""

# Standard library imports
from typing import Union
import math

# Third party imports
import scine_database as db
import scine_utilities as utils


def check_barrier_height(
    reaction, database_manager, model, structures, properties, max_barrier, min_barrier=-math.inf,
        barrierless_always_pass=True
) -> Union[db.ElementaryStep, None]:
    """
    Check if the barrier of any elementary step associated to the given reaction is below max_barrier.


    Parameters
    ----------
    reaction : scine_database.Reaction
        The reaction.
    database_manager : scine_database.Manager
        The database manager. Required for accessing the elementary steps.
    model : scine_database.Model
        The electronic structure model.
    structures : scine_utils.Collection
        The structure collection.
    properties : scine_utils.Collection
        The property collection.
    max_barrier : float
        The max. barrier threshold.
    min_barrier : float
        The min. barrier threshold (default -inf)
    barrierless_always_pass : bool
        Always allow barrier-less reactions.

    Returns
    -------
    Union[scine_database.ElementaryStep, None]
        The first elementary step that fulfills this condition barrier < max_barrier is returned. If the condition
        is never met, None is returned.
    """
    for elementary_step in reaction.get_elementary_steps(database_manager):
        if elementary_step.get_type() == db.ElementaryStepType.BARRIERLESS and barrierless_always_pass:
            return elementary_step
        barrier = get_single_barrier_for_elementary_step(
            elementary_step, model, structures, properties
        )
        if barrier is None:
            continue
        if max_barrier > barrier > min_barrier:
            return elementary_step
    return None


def get_single_barrier_for_elementary_step(
    step: db.ElementaryStep,
    model: db.Model,
    structures: db.Collection,
    properties: db.Collection,
) -> Union[float, None]:
    """
    Gives the barrier height of a single elementary step (left to right) in kJ/mol. If available, the gibbs free energy
    ('gibbs_free_energy') barrier is returned. Otherwise the electronic energy ('electronic_energy') barrier is
    returned. Returns None if both energies are unavailable.

    Parameters
    ----------
    step : scine_database.ElementaryStep (Scine::Database::ElementaryStep)
        The elementary step we want the barrier height from
    model : scine_database.Model
        The model used to calculate the energies.
    structures : scine_database.Collection
        The structure collection.
    properties : scine_database.Collection
        The property collection.

    Returns
    -------
    Union[float, None]
        barrier in kJ/mol
    """
    gibbs = get_single_barrier_for_elementary_step_by_type(
        step, "gibbs_free_energy", model, structures, properties
    )
    if gibbs is not None:
        return gibbs
    else:
        return get_single_barrier_for_elementary_step_by_type(
            step, "electronic_energy", model, structures, properties
        )


def get_energy_change(
        step: db.ElementaryStep,
        energy_type: str,
        model: db.Model,
        structures: db.Collection,
        properties: db.Collection,
) -> Union[None, float]:
    """
    Get the energy difference between educts and products for an elementary step.

    Parameters
    ----------
    step : db.ElementaryStep
        The elementary step.
    energy_type : str
        The energy label.
    model : db.Model
        The electronic structure model.
    structures : db.Collection
        The structure collection.
    properties : db.Collection
        The property collection.

    Returns
    -------
    Union[float, None]
        The difference between products and reactant energy. Returns None, if the energy is unavailable.
    """
    reactant_energies = [
        get_energy_for_structure(db.Structure(reactant), energy_type, model, structures, properties)
        for reactant in step.get_reactants(db.Side.LHS)[0]
    ]
    reactant_energy: Union[None, float] = None if None in reactant_energies else sum(reactant_energies)  # type: ignore
    product_energies = [
        get_energy_for_structure(db.Structure(product), energy_type, model, structures, properties)
        for product in step.get_reactants(db.Side.RHS)[1]
    ]
    product_energy: Union[None, float] = None if None in product_energies else sum(product_energies)  # type: ignore
    if not product_energy or not reactant_energy:
        return None
    return product_energy - reactant_energy


def get_single_barrier_for_elementary_step_by_type(
    step: db.ElementaryStep,
    energy_type: str,
    model: db.Model,
    structures: db.Collection,
    properties: db.Collection,
) -> Union[float, None]:
    """
    Gives the barrier height of a single elementary step (left to right) in kJ/mol for the specified energy type.
    Returns None if the energy type is not available.

    Parameters
    ----------
    step : scine_database.ElementaryStep (Scine::Database::ElementaryStep)
        The elementary step we want the barrier height from
    energy_type : str
        The name of the energy property such as 'electronic_energy' or 'gibbs_free_energy'
    model : scine_database.Model
        The model used to calculate the energies.
    structures : scine_database.Collection
        The structure collection.
    properties : scine_database.Collection
        The property collection.

    Returns
    -------
    Union[float, None]
        barrier in kJ/mol
    """
    reactant_energy = 0.0
    for reactant in step.get_reactants(db.Side.LHS)[0]:
        ret = get_energy_for_structure(db.Structure(reactant), energy_type, model, structures, properties)
        if ret is None:
            return None
        else:
            reactant_energy += ret
    if step.get_type() == db.ElementaryStepType.BARRIERLESS:
        product_energy = 0.0
        for product in step.get_reactants(db.Side.RHS)[1]:
            ret = get_energy_for_structure(db.Structure(product), energy_type, model, structures, properties)
            if ret is None:
                return None
            else:
                product_energy += ret
        if product_energy > reactant_energy:
            return (product_energy - reactant_energy) * utils.KJPERMOL_PER_HARTREE
        else:
            return 0.0
    ts = db.Structure(step.get_transition_state())
    ts_energy = get_energy_for_structure(ts, energy_type, model, structures, properties)
    if ts_energy is None:
        return None
    else:
        return (ts_energy - reactant_energy) * utils.KJPERMOL_PER_HARTREE


def get_energy_for_structure(
    structure: db.Structure,
    prop_name: str,
    model: db.Model,
    structures: db.Collection,
    properties: db.Collection,
) -> Union[float, None]:
    """
    Gives energy value depending on demanded property. If the property does not exit, None is returned.

    Parameters
    ----------
    structure : scine_database.Structure (Scine::Database::Structure)
        The structure we want the energy from
    prop_name : str
        The name of the energy property such as 'electronic_energy' or 'gibbs_free_energy'
    model : scine_database.Model
        The model used to calculate the energies.
    structures : scine_database.Collection
        The structure collection.
    properties : scine_database.Collection
        The property collection.

    Returns
    -------
    Union[float, None]
        energy value in Hartree
    """
    structure.link(structures)
    structure_properties = structure.query_properties(prop_name, model, properties)
    if not structure_properties:
        return None
    # pick last property if multiple
    prop = db.NumberProperty(structure_properties[-1])
    prop.link(properties)
    return prop.get_data()
