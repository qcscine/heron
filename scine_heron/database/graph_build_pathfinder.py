#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from typing import Iterator, List, Tuple, Union, Dict
from math import log
import networkx as nx
import numpy as np
from itertools import islice

import scine_database as db
from scine_heron.database.concentration_query_functions import query_reaction_flux, query_concentration


class Pathfinder:
    """
    A class to represent a list of reactions as graph and query this graph for simple paths between two nodes.
    In a simple path, every node part of the path is visited only once.

    Attributes
    ----------
    _calculations :: db.Collection
        Collection of the calculations of the connected database.
    _compounds :: db.Collection
        Collection of the compounds of the connected database.
    _reactions :: db.Collection
        Collection of the reactions of the connected database.
    _elementary_steps :: db.Collection
        Collection of the elementary steps of the connected database.
    _structures :: db.Collection
        Collection of the structures of the connected database.
    _properties :: db.Collection
        Collection of the properties of the connected database.
    graph_handler
        A class handling the construction of the graph. Can be adapted to ones needs.
    _use_old_iterator :: bool
        Bool to indicate if the old iterator shall be used querying for paths between a source - target pair.
    _unique_iterator_memory :: Tuple[str, str, Iterator]
        Memory of iterator with source and target string as well as the iterator.
    start_compounds :: List[str]
        A list containing the compounds which are present at the start.
    start_compounds_set :: bool
        Bool to indicate if start_compounds is set.
    _pseudo_inf :: float
        Float for edges with infinite weight.
    compound_costs :: Dict[str, float]
        A dictionary containing the cost of the compounds with the compounds as keys.
    compound_costs_solved :: bool
        Bool to indicate if all compounds have a compound cost.
    """

    def __init__(self, db_manager: db.Manager):
        self.options = self.Options()
        self.manager = db_manager
        # Get required collections
        self._calculations = db_manager.get_collection('calculations')
        self._compounds = db_manager.get_collection('compounds')
        self._reactions = db_manager.get_collection('reactions')
        self._elementary_steps = db_manager.get_collection('elementary_steps')
        self._structures = db_manager.get_collection('structures')
        self._properties = db_manager.get_collection('properties')

        self.graph_handler: Union[Pathfinder.BasicHandler, None] = None
        # attribute to store iterator employed in find_unique_paths; path_object, iterator
        self._use_old_iterator = False
        self._unique_iterator_memory: Union[Tuple[Tuple[List[str], float],
                                                  Iterator], None] = None

        # Compound costs
        self.start_compounds: List[str] = []
        self.start_compounds_set = False
        self._pseudo_inf = 1e12
        self.compound_costs: Dict[str, float] = {}
        self.compound_costs_solved = False

    class Options:
        """
        A class to vary the setup of Pathfinder.
        """
        __slots__ = {"graph_handler", "barrierless_weight", "use_energy_threshold", "energy_threshold"}

        def __init__(self):
            self.graph_handler = "basic"  # pylint: disable=no-member
            self.barrierless_weight = 1.0
            # in kJ / mol
            self.use_energy_threshold = False
            self.energy_threshold = 100

    @staticmethod
    def get_valid_graph_handler_options() -> List[str]:
        return ["basic", "flux"]

    def _construct_graph_handler(self):
        """
        Constructor for the graph handler.

        Raises
        ------
        RuntimeError
            Invalid options for graph handler.
        """
        if not self.graph_handler:
            if self.options.graph_handler not in self.get_valid_graph_handler_options():
                raise RuntimeError("Invalid graph handler option.")
            if self.options.graph_handler == "basic":
                self.graph_handler = self.BasicHandler(self.manager)
                self.graph_handler.barrierless_weight = self.options.barrierless_weight
            elif self.options.graph_handler == "flux":
                self.graph_handler = self.FluxRxnAdder(self.manager)

    def _reset_iterator_memory(self):
        """
        Reset memory for unique memory.
        """
        self._unique_iterator_memory = None

    # Build graph function from reaction list
    def build_graph(self):
        """
        Build the nx.DiGraph() from a list of filtered reactions.
        """
        self._reset_iterator_memory()
        self._construct_graph_handler()
        assert self.graph_handler
        for rxn_id in self.graph_handler.get_valid_reaction_ids():
            rxn = db.Reaction(rxn_id, self._reactions)
            self.graph_handler.add_rxn(rxn)

    def find_paths(self, source: str, target: str, n_requested_paths: int = 3,
                   n_skipped_paths: int = 0) -> List[Tuple[List[str], float]]:
        """
        Query the build graph for simple paths between a source and target node.

        Notes
        -----
        * Requires a built graph

        Parameters
        ----------
        source :: str
            The ID of the starting compound as string.
        target :: str
            The ID of the targeted compound as string.
        n_requested_paths :: int, optional
            Number of requested paths, by default 3
        n_skipped_paths :: int, optional
            Number of skipped paths from, by default 0. Allows to set starting point of query.

        Returns
        -------
        found_paths :: List[Tuple[List[str], float]]
            List of paths where each path consists of two information, the list of nodes of the path and its length.
        """
        assert self.graph_handler
        found_paths = []
        for path in self._k_shortest_paths(self.graph_handler.graph, source, target, n_requested_paths,
                                           weight="weight", path_start=n_skipped_paths):
            path_length = nx.path_weight(self.graph_handler.graph, path, "weight")
            found_paths.append((path, path_length))

        return found_paths

    def find_unique_paths(self, source: str, target: str, number: int = 3) -> List[Tuple[List[str], float]]:
        """
        Find a unique number of paths from a given source node to a given target node.
        Unique meaning that different paths (sequence of nodes) can have the same total weight.
        If one is solely interested in one path of paths with identical weight which can interpreted in the easiest
        human readable way, the shortest (in terms of length) longest (in terms of number of nodes) path is returned.
        Returning the path of a set of paths (maximum set size is set to 10) with the same weight with the most nodes
        guarantees that.

        Notes
        -----
        * Checks if a stored iterator for the given source-target pair should be used.

        Parameters
        ----------
        source :: str
            The ID of the starting compound as string.
        target :: str
            The ID of the targeted compound as string.
        number :: int
            The number of unique paths to be returned. Per default, 3 paths are returned.

        Returns
        -------
        path_tuple_list :: List[Tuple[List[str], float]]
            List of paths where each path consists of two information, the list of nodes of the path and its length.
        """
        assert self.graph_handler
        counter = 0
        path_tuple_list = list()
        # # # Initialise iterator over shortest simple paths if it is either not set or source/target do not match
        if not self._use_old_iterator or \
           self._unique_iterator_memory is None or \
           self._unique_iterator_memory[0][0][0] != source or \
           self._unique_iterator_memory[0][0][-1] != target:
            path_iterator = iter(nx.shortest_simple_paths(self.graph_handler.graph, source, target, weight="weight"))
            # # # Find first path and its cost
            old_path = next(path_iterator)
            old_path_cost = nx.path_weight(self.graph_handler.graph, old_path, weight="weight")
        else:
            path_iterator = self._unique_iterator_memory[1]
            old_path = self._unique_iterator_memory[0][0]
            old_path_cost = self._unique_iterator_memory[0][1]

        while counter < number:
            same_cost = True
            tmp_path_list: List[List[str]] = list()
            # # # Collect all paths with same cost
            # TODO: Parameter for max tmp paths
            n_max_collected_paths = 10
            while same_cost and len(tmp_path_list) < n_max_collected_paths:
                # # # Append old path to tmp_path list
                tmp_path_list.append(old_path)
                # # # Get next path and its cost
                new_path = next(path_iterator, None)
                # # # Break loop if no path is returned
                if new_path is None:
                    break
                new_path_cost = nx.path_weight(self.graph_handler.graph, new_path, weight="weight")
                # # # Check if new cost different to old cost
                if abs(old_path_cost - new_path_cost) > 1e-12:
                    same_cost = False
                # # # Overwrite old path with new path
                old_path = new_path

            # # # Append path with most nodes to tuple list and its cost
            path_tuple_list.append((max(tmp_path_list, key=lambda x: len(x)),  # pylint: disable=unnecessary-lambda
                                    old_path_cost))
            # # # Break counter loop if no more paths to target are found
            if new_path is None:
                break
            old_path_cost = new_path_cost
            counter += 1
        # # # Store iterator and path info (list of nodes and length)
        if new_path is not None:
            self._unique_iterator_memory = ((new_path, new_path_cost), path_iterator)
        return path_tuple_list

    @staticmethod
    def _k_shortest_paths(graph: nx.DiGraph, source: str, target: str, n_paths: int, weight: Union[str, None] = None,
                          path_start: int = 0) -> List[List[str]]:
        """
        Finding k shortest paths between a source and target node in a given graph.
        The length of the returned paths increases.

        Notes
        -----
        * This procedure is based on the algorithm by Jin Y. Yen [1]. Finding the first k paths requires O(k*nodes^3)
          operations.
        * Implemented as given in the documentation of NetworkX:
          https://networkx.org/documentation/stable/reference/algorithms/generated/ \
          networkx.algorithms.simple_paths.shortest_simple_paths.html
        * [1]: Jin Y. Yen, “Finding the K Shortest Loopless Paths in a Network”, Management Science, Vol. 17, No. 11,
               Theory Series (Jul., 1971), pp. 712-716.

        Parameters
        ----------
        graph :: nx.DiGraph
            The graph to be queried.
        source :: str
            The ID of the starting compound as string.
        target :: str
            The ID of the targeted compound as string.
        n_paths :: int
            The number of paths to be returned.
        weight :: Union[str, None], optional
            The key for the weight encoded in the edges to be used.
        path_start :: int, optional
            An index of the first returned path, by default 0

        Returns
        -------
        List[List[str]]
            List of paths, each path consisting of a list of nodes.
        """
        return list(
            islice(nx.shortest_simple_paths(graph, source, target, weight=weight), path_start, path_start + n_paths)
        )

    def set_start_conditions(self, conditions: Dict[str, float]):
        """
        Add the IDs of the start compounds to self.start_compounds and add entries for cost in self.compound_cost.

        Parameters
        ----------
        conditions :: Dict
            The IDs of the compounds as keys and its given cost as values.
        """
        # # # Reset Start conditions, if already set previously
        if self.start_compounds_set:
            self.compound_costs = {}
            self.start_compounds = []
        # # # Loop over conditions and set them
        for cmp_id, cmp_cost in conditions.items():
            self.compound_costs[cmp_id] = cmp_cost
            self.start_compounds.append(cmp_id)
        self.start_compounds_set = True

    def __weight_func(self, u: str, _: str, d: Dict):
        """
        Calculates the weight of the edge d connecting u with _ (directional!).
        Only consider the costs of the required compounds if the edge d is from a compound node to a reaction node.
        If the edge d connects a reaction node with a compound node, the returned weight should be 0.

        Parameters
        ----------
        u :: str
            The ID of start node.
        _ :: str
            The ID of end node.
        d :: Dict
            The edge connecting u and _ as dictionary

        Returns
        -------
        float
            Sum over the edge weight and the costs of the required compounds.
        """
        # # # Weight of edge
        edge_wt = d.get("weight", 0)
        # # # List of required compounds
        tmp_required_compounds = d.get("required_compounds", None)
        # # # Sum over costs of required compounds.
        # # # Only for edges from compound node to rxn node
        if ';' not in u and tmp_required_compounds is not None:
            required_compound_costs = np.sum([self.compound_costs[n] for n in tmp_required_compounds])
        else:
            required_compound_costs = 0.0

        return edge_wt + required_compound_costs

    def calculate_compound_costs(self, recursive: bool = True):
        """
        Determine the cost for all compounds via determining their shortest paths from the self.start_compounds.
        If this succeeds, set self.compound_costs_solved to True. Otherwise it stays False.

        The algorithm works as follows:
        Given the starting conditions, one loops over the individual starting compounds as long as:
            - the self._pseudo_inf entries in self.compound_costs are reduced
            - for any entry in self.compounds_cost a lower cost is found
        With each starting compound, one loops over compounds which have yet no cost assigned.
        For each start - target compound pair, the shortest path is determined employing Dijkstra's algorithm.
        The weight function checks the 'weight' of the edges as well as the costs of the required compounds listed in
        the 'required_compounds' of the traversed edges.
        If the path exceeds the length of self._pseudo_inf, this path is not considered for further evaluation.
        The weight of the starting compound is added to the tmp_cost.
        If the target compound has no weight assigned yet in 'self.compound_costs' OR
        if the target compound has a weight assigned which is larger (in 'self.compound_costs' as well as in
        'tmp_compound_costs') than the current 'tmp_cost' is written to the temporary storage of 'tmp_compound_costs'.

        After the loop over all starting compounds completes, the collected costs for the found targets are written to
        self.compound_costs.
        The convergence variables are updated and the while loop continues.

        Parameters
        ----------
        recursive :: bool
            All compounds are checked for shorter paths, True by default.
            If set to False, compounds for which a cost has been determined are not checked in the next loop.
        """
        assert self.graph_handler
        if not self.start_compounds_set:
            raise RuntimeError("No start conditions given")
        if len(self.graph_handler.graph.nodes) == 0:
            raise RuntimeError("No nodes in graph")
        cmps_to_check = [n for n in self.graph_handler.graph.nodes if ';' not in n
                         and n not in self.start_compounds]
        # # # Set all compounds to be checked to pseudo inf cost
        for cmp_id in cmps_to_check:
            self.compound_costs[cmp_id] = self._pseudo_inf
        # # # Dictionary for current run
        tmp_compound_costs: Dict[str, float] = {}
        # # # Determine convergence variables for while loop
        current_inf_count = sum(value == self._pseudo_inf for value in self.compound_costs.values())
        prev_inf_count = current_inf_count
        # # # Convergence criteria
        compound_costs_change = None
        compound_costs_opt_change = 1
        converged = False
        # # # Find paths until either no costs are unknown or the None count has not changed
        while (not converged):
            compound_costs_opt_change = 0
            print("Remaining Nodes:", len(cmps_to_check))
            for tmp_start_node in self.start_compounds:
                # # # Loop over all nodes to be checked starting from start nodes
                for target in cmps_to_check:
                    # # # Determine cost and path with dijkstra's algorithm
                    tmp_cost, _ = nx.single_source_dijkstra(self.graph_handler.graph, tmp_start_node, target,
                                                            cutoff=None, weight=self.__weight_func)
                    # # # Check if the obtained cost is larger than infinity (pseudo_inf)
                    # # # and continue with the next target if this is the case
                    if (tmp_cost - self._pseudo_inf) > 0.0:
                        continue
                    # # # Add cost of the starting node
                    tmp_cost += self.compound_costs[tmp_start_node]
                    # # # Check for value in compound_costs dict and
                    if (self.compound_costs[target] != self._pseudo_inf and
                            10e-6 < self.compound_costs[target] - tmp_cost):
                        compound_costs_opt_change += 1
                    # # # Not already set check
                    if self.compound_costs[target] == self._pseudo_inf or (
                            self.compound_costs != self._pseudo_inf and 10e-6 < self.compound_costs[target] - tmp_cost):
                        # # # Not discovered in current run OR new tmp cost lower than stored cost
                        if (target not in tmp_compound_costs.keys()):
                            tmp_compound_costs[target] = tmp_cost
                        elif (tmp_cost < tmp_compound_costs[target]):
                            tmp_compound_costs[target] = tmp_cost
            # # # Write obtained compound_costs to overall dictionary
            for key, value in tmp_compound_costs.items():
                self.compound_costs[key] = value
                # # # Remove found nodes if recursive is false
                if not recursive:
                    cmps_to_check.remove(key)
            # # # Reset tmp_pr_cost
            tmp_compound_costs = {}
            # # # Convergence Check
            current_inf_count = sum(value == self._pseudo_inf for value in self.compound_costs.values())
            compound_costs_change = prev_inf_count - current_inf_count
            prev_inf_count = current_inf_count

            print(50 * '-')
            print("Current None:", current_inf_count)
            print("PR Change:", compound_costs_change)
            print("PR Opt Change:", compound_costs_opt_change)
            # # # Convergence Check
            if (compound_costs_change == 0 and compound_costs_opt_change == 0):
                converged = True

        # # # Final check if all compound costs are solved
        if current_inf_count == 0:
            self.compound_costs_solved = True

    def update_graph_compound_costs(self):
        """
        Update the 'weight' of edges from compound to reaction nodes by adding the compound costs.
        The compound costs are the sum over the costs stored in self.compound_costs of the required compounds.
        The edges of the resulting graph contain a weight including the required_compound_costs based on the starting
        conditions.
        All analysis of the graph therefore depend on the starting conditions.
        """

        # # # Check if all costs are available
        if not self.compound_costs_solved:
            unsolved_cmp = [key for key, _ in self.compound_costs.items()]
            raise RuntimeError("The following cmp have no cost assigned:\n" + str(unsolved_cmp) +
                               "\nReconsider the starting conditions.")
        # # # Reset unique_iterator_list as graph changes
        self._reset_iterator_memory()
        for node in self.compound_costs.keys():
            # # # Loop over all edges of compound and manipulate weight
            for target_node, attributes in self.graph_handler.graph[node].items():
                required_compound_costs = np.asarray([self.compound_costs[k] for k in attributes['required_compounds']])
                tot_required_compound_costs = np.sum(required_compound_costs)
                # # # Set required compound costs in edge
                self.graph_handler.graph.edges[node,
                                               target_node]['required_compound_costs'] = tot_required_compound_costs
                # # # Add required compound costs to weight
                self.graph_handler.graph.edges[node, target_node]['weight'] += tot_required_compound_costs

    # Base Class for adding a reaction; up weight to rxn node is just one per default, no further info
    class BasicHandler:
        """
        A basic class to handle the construction of the nx.DiGraph.
        A list of reactions can be added differently, depending on the implementation of _get_weight and
        get_valid_reaction_ids.
        """

        def __init__(self, manager: db.Manager):
            self.graph = nx.DiGraph()
            self.db_manager = manager
            self.barrierless_weight = 1.0
            self._compounds = self.db_manager.get_collection("compounds")
            self._flasks = self.db_manager.get_collection("flasks")
            self._structures = self.db_manager.get_collection("structures")
            self._properties = self.db_manager.get_collection("properties")
            self._reactions = self.db_manager.get_collection("reactions")

        def add_rxn(self, reaction: db.Reaction):
            """
            Add a reaction to the graph.
            Each reaction node represents the LHS and RHS.
            Hence every reagent of a reaction is connected to every product of a reaction via one reaction node.
            For instance:
            A + B = C + D, reaction R
            A -> R_1 -> C
            A -> R_1 -> D
            B -> R_1 -> C
            B -> R_1 -> D

            C -> R_2 -> A
            C -> R_2 -> B
            D -> R_2 -> A
            D -> R_2 -> B

            Representing this reaction in the graph yields 4 compound nodes,
            2 reaction nodes (same reaction) and 16 edges (2*2*2*2).
            The weights assigned to the edges depends on the _get_weight implementation.

            The edges from a compound node to a reaction node contain several information:
                weight: the weight of the edge
                        1 if the reaction is not barrierless, otherwise it is set to self.barrierless_weight
                required_compounds: the IDs of the other reagents of this side of the reaction in a list
                required_compound_costs: the sum over all compound costs of the compounds in the required_compounds list
                                         None by default.

            The edges from a reaction node to a compound node contain several information:
                weight: the weight of the edge, set to 0
                required_compounds: the IDs of the other products emerging;
                                        added for easier information extraction during the path analysis

            Parameters
            ----------
            reaction :: db.Reaction
                The reaction to be added to the graph.
            """
            # Add two rxn nodes
            rxn_nodes = []
            reaction_id = reaction.id().string()

            for i in range(0, 2):
                # Add rxn node between lhs and rhs compound
                rxn_node = ';'.join([reaction_id, str(i)])
                rxn_node += ';'
                self.graph.add_node(rxn_node, color='rxn_node')
                rxn_nodes.append(rxn_node)
            # Convert to strings
            reactants = reaction.get_reactants(db.Side.BOTH)
            reactant_types = reaction.get_reactant_types(db.Side.BOTH)
            weights = self._get_weight(reaction)
            # Add lhs aggregates and connect
            for lhs_cmp, lhs_type in zip([i.string() for i in reactants[0]],
                                         [i.name for i in reactant_types[0]]):
                if lhs_cmp not in self.graph:
                    self.graph.add_node(lhs_cmp, type=lhs_type)
                required_cmps_lhs = [s.string() for s in reactants[0]]
                required_cmps_lhs.remove(lhs_cmp)
                self.graph.add_edge(lhs_cmp, rxn_nodes[0], weight=weights[0], required_compounds=required_cmps_lhs,
                                    required_compound_costs=None)
                self.graph.add_edge(rxn_nodes[1], lhs_cmp, weight=0.0, required_compounds=None)
            # Add rhs aggregates and connect
            for rhs_cmp, rhs_type in zip([i.string() for i in reactants[1]],
                                         [i.name for i in reactant_types[1]]):
                if rhs_cmp not in self.graph:
                    self.graph.add_node(rhs_cmp, type=rhs_type)
                required_cmps_rhs = [s.string() for s in reactants[1]]
                required_cmps_rhs.remove(rhs_cmp)
                self.graph.add_edge(rhs_cmp, rxn_nodes[1], weight=weights[1], required_compounds=required_cmps_rhs,
                                    required_compound_costs=None)
                self.graph.add_edge(rxn_nodes[0], rhs_cmp, weight=0.0, required_compounds=None)

            # # # Loop over reaction nodes to add required compounds info to downwards edges; might be unnecessary
            node_index = 1
            for node in rxn_nodes:
                for key in self.graph[node].keys():
                    self.graph.edges[node, key]['required_compounds'] = \
                        self.graph.edges[key, rxn_nodes[node_index]]['required_compounds']
                node_index -= 1

        def _get_weight(self, reaction: db.Reaction) -> Tuple[float, float]:
            """
            Determining the weights for the edges of the given reaction.

            Parameters
            ----------
            reaction :: db.Reaction
                Reaction of interest

            Returns
            -------
            Tuple[float, float]
                Weight for connections to the LHS reaction node, weight for connections to the RHS reaction node
            """
            for step in reaction.get_elementary_steps(self.db_manager):
                # # # Barrierless weights for barrierless reactions
                if step.get_type() == db.ElementaryStepType.BARRIERLESS:
                    return self.barrierless_weight, self.barrierless_weight
            return 1.0, 1.0

        def get_valid_reaction_ids(self) -> List[db.ID]:
            """
            Basic filter function for reactions.
            Per default it returns all reactions.

            Returns
            -------
            List[db.ID]
                List of IDs of the filtered reactions.
            """
            valid_ids: List[db.ID] = list()
            for reaction in self._reactions.iterate_all_reactions():
                valid_ids.append(reaction.id())
            return valid_ids

    class FluxRxnAdder(BasicHandler):
        def __init__(self, manager: db.Manager):
            """
            Edge weights based on the the reaction flux from a kinetic modeling calculation.
            """
            super().__init__(manager)
            self._calculations = manager.get_collection("calculations")
            self._forward_flux_label = "_forward_edge_flux"
            self._backward_flux_label = "_backward_edge_flux"
            self._zero_break_scale = 1e-4
            self._kinetic_modeling_job_order = "kinetx_kinetic_modeling"
            self._reaction_id_key = "reaction_ids"

        def _valid_reaction(self, reaction: db.Reaction) -> bool:
            forward_flux = query_reaction_flux(self._forward_flux_label, reaction, self._compounds, self._flasks,
                                               self._structures, self._properties)
            return forward_flux > 0.0

        def _get_weight(self, reaction: db.Reaction) -> Tuple[float, float]:
            forward_flux = query_reaction_flux(self._forward_flux_label, reaction, self._compounds, self._flasks,
                                               self._structures, self._properties)
            backward_flux = query_reaction_flux(self._forward_flux_label, reaction, self._compounds, self._flasks,
                                                self._structures, self._properties)
            # catch zeros.
            forward_flux = max(forward_flux, 1e-6)
            backward_flux = max(backward_flux, 1e-6)
            # The flux is a direct measure of the conditional probability to traverse the reaction.
            # However, it is not normalized to be in [0, 1] but rather in [0, inf]. Therefore, we scale the
            # approximate probability by a factor that should (more or less) shift the flux into the interval [0, 1].
            p_forward = self._zero_break_scale * forward_flux
            p_backward = self._zero_break_scale * backward_flux
            # The information value (or surprise) of the event (traversal of the reaction) may then be given by
            # -log(p) (this is adapted from the definition of the Shannon entropy, i.e. S = <-log(p)>).
            return max(-log(p_forward), 0.0), max(-log(p_backward), 0.0)

        def get_valid_reaction_ids(self) -> List[db.ID]:
            last_calculation = self._get_last_completed_calculation()
            if last_calculation is not None:  # last_calculation may be None.
                reaction_str_ids: List[str] = last_calculation.get_setting(self._reaction_id_key)  # type: ignore
                if len(reaction_str_ids) > 0:
                    # The reactions must be valid. We quickly check the first one.
                    check_reaction = db.Reaction(db.ID(reaction_str_ids[0]), self._reactions)
                    if self._valid_reaction(check_reaction):
                        return [db.ID(str_id) for str_id in reaction_str_ids]
            return []

        def _get_last_completed_calculation(self) -> Union[None, db.Calculation]:
            start_structure = self._get_one_input_structure()
            if start_structure:
                calculation_ids = start_structure.get_calculations(self._kinetic_modeling_job_order)
                for calculation_id in reversed(calculation_ids):
                    calculation = db.Calculation(calculation_id, self._calculations)
                    if calculation.get_status() != db.Status.COMPLETE:
                        continue
                    return calculation
            return None

        def _get_one_input_structure(self) -> Union[db.Structure, None]:
            for compound in self._compounds.iterate_all_compounds():
                compound.link(self._compounds)
                centroid = db.Structure(compound.get_centroid(), self._structures)
                start_concentration = query_concentration("start_concentration", centroid, self._properties)
                if start_concentration > 0.0:
                    return centroid
            return None
