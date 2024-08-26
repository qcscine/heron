Changelog
=========

Release 2.0.0
-------------
New features:
  - Add SCINE Chemoton tab to run explorations from within Heron
  - Add tab to run the Chemoton Steering Wheel
  - Add SCINE ReaDuct tab to carry out any ReaDuct task (e.g., structure optimizations)
  - Modify Interactive to run with any SCINE backend calculator
  - Add QM/MM capabilities, SFAM parametrization, and automated QM region selection to Interactive including database support
  - Add option to construct Chemoton aggregate and reactive site filters
  - Add option to store and generate reaction templates for SCINE Art
  - Add possibility to slice trajectories
  - Select and move multiple atoms in Interactive
  - Add activate/deactive buttons to compounds in network view for rudimentary exploration control
  - Allow direct connection to a database at start-up from the command line
  - Introduce binary and human readable save formats for some tabs
  - Added package variants for easier installation of optional requirements
  - Generate graph of the entire CRN or import graph of the CRN for efficient processing purposes
  - Introduced cache for every local CRN around a centroid; once built, it can be easily accessed again
  - Enable fast filtering on barriers, flux, or date created (can be easily expanded to other filters)
  - Reactions trajectory consistently extends from the center to the outer node
  - Highlighting connected nodes when clicking on them
  - Add new color style, `legacy`, based on Chemoton 1.0 colors
  - Carry out steering wheel preview in background with progress bar with time estimate. The preview query can be aborted should it take too long
  - Format reaction equation in path energy level widget
  - Add timeout option for shortest path search, allowing users to easily interrupt lengthy searches if needed
  - Add support for StructureFilter
  - Add support for changed GearOptions
  - Add AggregateFilter to database viewer tab

Changes:
  - Extend graph building capabilities
  - Improve visualization of (shortest) path searches
  - Improve error messaging
  - Moved database queries to the SCINE Database module
  - Rename 'Molecular Viewer' to 'Interactive'
  - Node positions are now efficiently determined by algorithms implemented in Networkx
  - Status bar in graph traversal is now identical to the main status bar
  - Implement new caching logic for shortest paths, storing paths with and without two reactions in a path
  - Add support for `ElementaryStepFilter` and `ReactionFilter` required by Chemoton 4.0.0.

Bugfixes:
  - Handle the case of loading a completely empty database
  - Prevent overlapping nodes in reactions
  - Implement plateaus in spline representation to enhance visualization
  - Being capable of representing local CRNs with more than 100 nodes

Technical:
  - Removed complicated code for positioning compound and reaction nodes, improving code readability and maintainability
  - Functionalized individual parts to render and position nodes
  - Functionalized reaction profile and cleaned up redundant code
  - Employed energy diagram class for plateaus in reaction profile
  - Removed substep_callback in Worker
  - Update address in license

Release 1.0.0
-------------

Initial Features:
^^^^^^^^^^^^^^^^^

- Main Molecular Viewer
    - Real-time calculations of energies and forces (using SCINE Sparrow)
    - Haptic device support
    - Real-time energy plot
    - Basic molecular building/editing
    - Isosurface plots of orbitals and densities
- Reaction Network Viewer
    - Excerpt view of Aggregates and Reactions
    - Basic filtering options based on reaction energies
    - Navigation around a single centered Aggregate
    - (Shortest) path searches based on Aggregate IDs
    - Expansion tab for Aggregates (showing contained Structures)
    - Expansion tab for Reactions (showing contained Elementary Steps)
    - SVG export of all graph views
- SCINE Database Statistics
    - Database content statistics
    - Calculation status statistics
    - Runtime histogram
- SCINE Database Browser
    - Listing, searching and displaying of individual database entries
       - Reaction and Elementary Steps
       - Compounds and single-molecule Structures
       - Flasks and multi-molecule complexes (also Structures)

