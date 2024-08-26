#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

# Standard library imports
from typing import Union, Tuple, Optional
import math
import numpy as np

# Third party imports
import scine_database as db
import scine_utilities as utils

from warnings import warn
warn('This is deprecated, please import the queries from scine_database', DeprecationWarning, stacklevel=2)


def check_barrier_height(
        reaction: db.Reaction,
        database_manager: db.Manager,
        model: db.Model,
        structures: db.Collection,
        properties: db.Collection,
        max_barrier: float,
        min_barrier: float = -math.inf,
        barrierless_always_pass: bool = True)\
        -> Union[db.ElementaryStep, None]:
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
        if not elementary_step.has_transition_state() and barrierless_always_pass:
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
    if not step.has_transition_state():
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


def get_energy_sum_of_elementary_step_side(step: db.ElementaryStep, side: db.Side, energy_type: str, model: db.Model,
                                           structures: db.Collection, properties: db.Collection) -> Union[float, None]:
    """
    Gives the total energy in atomic units of the given side of the step. Returns None if the energy type is
    not available.

    Parameters
    ----------
    step : scine_database.ElementaryStep (Scine::Database::ElementaryStep)
        The elementary step we want the energy from
    side : scine_database.Side (Scine::Database::Side)
        The side we want the side from
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
        Energy in hartree
    """
    if side == db.Side.BOTH:
        raise RuntimeError("The energy sum of both sides of a step is not supported.")
    index = 0 if side == db.Side.LHS else 1
    energies = [
        get_energy_for_structure(db.Structure(reactant), energy_type, model, structures, properties)
        for reactant in step.get_reactants(side)[index]
    ]
    return None if None in energies else sum(energies)  # type: ignore


def get_elementary_step_with_min_ts_energy(reaction: db.Reaction,
                                           energy_type: str,
                                           model: db.Model,
                                           elementary_steps: db.Collection,
                                           structures: db.Collection,
                                           properties: db.Collection,
                                           max_barrier: float,
                                           min_barrier=-math.inf,
                                           structure_model: Optional[db.Model] = None) -> Optional[db.ElementaryStep]:
    """
    Gets the elementary step ID with the lowest energy of the corresponding transition state of a reaction.


    Parameters
    ----------
    reaction : db.Reaction
        The reaction for which the elementary steps shall be analyzed.
    energy_type : str
        The name of the energy property such as 'electronic_energy' or 'gibbs_free_energy'
    model : scine_database.Model
        The model used to calculate the energies.
    elementary_steps : db.Collection
        The elementary step collection.
    structures : scine_database.Collection
        The structure collection.
    properties : scine_database.Collection
        The property collection.
    max_barrier : float
        The maximum allowed barrier
    min_barrier : float
        The minimum allowed barrier, default is negative infinity
    structure_model : Optional[db.Model]
        The model of the transition state. If None, the model of the transition state is not checked.

    Returns
    -------
    Union[db.ElementaryStep, None]
        The elementary step with the lowest TS energy.
    """
    lowest_ts_energy = np.inf
    es_id_with_lowest_ts = None
    # # # Loop over elementary steps
    for es_id in reaction.get_elementary_steps():
        es = db.ElementaryStep(es_id, elementary_steps)
        # # # Type check elementary step and break if barrierless
        if es.get_type() == db.ElementaryStepType.BARRIERLESS:
            first_structure_lhs = db.Structure(es.get_reactants()[0][0], structures)
            if structure_model is not None and first_structure_lhs.get_model() != structure_model:
                continue
            # # # Energy Check for minima
            first_structure_lhs_energy = get_energy_for_structure(first_structure_lhs, energy_type, model,
                                                                  structures, properties)
            if first_structure_lhs_energy is None:
                continue
            es_id_with_lowest_ts = es_id
            break
        ts = db.Structure(es.get_transition_state(), structures)
        if structure_model is not None and ts.get_model() != structure_model:
            continue

        # # # Costly safety check that barrier as well as ts_energy exist for this model and energy type
        ts_energy = get_energy_for_structure(
            ts, energy_type, model, structures, properties)
        barriers = get_barriers_for_elementary_step_by_type(es, energy_type, model, structures, properties)
        if None in barriers or ts_energy is None:
            continue
        # Check min/max barrier are correct, check next elementary step
        if any(barrier > max_barrier or barrier < min_barrier for barrier in barriers):  # type: ignore
            continue
        # # # Comparison with current lowest energy
        if ts_energy < lowest_ts_energy:
            es_id_with_lowest_ts = es_id
            lowest_ts_energy = ts_energy
    if es_id_with_lowest_ts is not None:
        return db.ElementaryStep(es_id_with_lowest_ts, elementary_steps)
    else:
        return None


def get_barriers_for_elementary_step_by_type(step: db.ElementaryStep, energy_type: str, model: db.Model,
                                             structures: db.Collection, properties: db.Collection)\
        -> Union[Tuple[float, float], Tuple[None, None]]:
    """
    Gives the forward and backward barrier height of a single elementary step (left to right) in kJ/mol for the
    specified energy type. Returns None if the energy type is not available.

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
    Union[Tuple[float, float], Tuple[None, None]]
        Barriers in kJ/mol
    """
    reactant_energy = get_energy_sum_of_elementary_step_side(step, db.Side.LHS, energy_type, model,
                                                             structures, properties)
    if reactant_energy is None:
        return None, None
    product_energy = get_energy_sum_of_elementary_step_side(step, db.Side.RHS, energy_type, model,
                                                            structures, properties)
    if product_energy is None:
        return None, None
    if step.get_type() == db.ElementaryStepType.BARRIERLESS:
        if product_energy > reactant_energy:
            return (product_energy - reactant_energy) * utils.KJPERMOL_PER_HARTREE, 0.0
        else:
            return 0.0, (reactant_energy - product_energy) * utils.KJPERMOL_PER_HARTREE
    ts = db.Structure(step.get_transition_state())
    ts_energy = get_energy_for_structure(ts, energy_type, model, structures, properties)
    if ts_energy is None:
        return None, None
    lhs_barrier = (ts_energy - reactant_energy) * utils.KJPERMOL_PER_HARTREE
    rhs_barrier = (ts_energy - product_energy) * utils.KJPERMOL_PER_HARTREE
    return lhs_barrier, rhs_barrier
