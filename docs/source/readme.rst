.. image:: ../../scine_heron/resources/heron_logo.png
   :alt: SCINE Heron

Introduction
------------

SCINE Heron is the graphical user interface for all other SCINE modules. It has six main ways of operation:

1) One can explore chemical reactivity immersively and interactively based on first principles in real-time. The
graphical user interface of SCINE Heron displays a three-dimensional molecular structure and allows users
to interact with it. They can induce structural changes with a computer mouse or a haptic device and perceive
the effect of their manipulations immediately through visual and/or haptic feedback. For fast electronic
structure calculations, we employ currently different semi-empirical methods, which can deliver properties
in the millisecond timescale, while providing a qualitatively correct description of the potential energy surface.

2) One can construct a system-focused atomistic model (SFAM), i.e., a force field parametrized on Hessian calculations
on the specific system. SFAM force fields can be employed in the interactive setting either as a stand-alone or
in a hybrid QM/MM model. The hybrid model can also be constructed within the graphical user interface either by our
automated QM region selection algorithm or by manual selection of the QM region by clicking on the QM atoms.

3) One can launch individual energy calculations and optimization routines, such as transition state searches,
with any backend program supported in SCINE, in the ReaDuct tab. The input structures can be read-in from file
or stem directly from Interactive or an explored reaction network.

4) One can automaticaly determine the active space for multi-configurational calculations with autoCAS.
Based on orbital entanglement measures derived from an approximate DMRG wave function, autoCAS identifies all strongly
correlated orbitals to be included in the active space of a final, converged calculation.

5) One can interact with explorations done by SCINE Chemoton. One can visualize the chemical reaction
network without drowning in too much information. For example, one can selectively display reactions with a
barrier lower than a certain, user-specified threshold. Furthermore, one can analyze all compounds and reactions
discovered, e.g., for reactions, one can visualize the trajectory and study the energy along it. It is also possible
to search and visualize all pathways between two given compounds. Any compound discovered by Chemoton can be
transferred to the interactive part of the GUI, allowing it to be further studied.

6) One can carry out reaction explorations directly in the graphical user interface by either constructing individual
Chemoton engines, or by relying on the Steering Wheel mechanism that lets one guide the automated exploration more closely.
The exploration can be constrained by additional aggregate and reactive site filters that can also be constructed in the
graphical user interface. Almost all of the exploration guidances in Heron support I/O operations which allow to save
and reuse individual parts for other explorations or restarts.

License and Copyright Information
---------------------------------

For license and copyright information, see the file ``LICENSE.txt`` in the source
directory.

Installation
------------

.. include:: installation.rst
   :start-after: inclusion-marker-do-not-remove

Usage
-----

.. include:: usage.rst
   :start-after: inclusion-marker-do-not-remove

Haptic Device
-------------

.. include:: haptics.rst
   :start-after: inclusion-marker-do-not-remove

How to Cite
-----------

When publishing results obtained with Heron, please cite the corresponding
release as archived on `Zenodo <https://zenodo.org/records/7038388>`_ (please use the DOI of
the respective release) and the following paper:

C. H. Müller, M. Steiner, J. P. Unsleber, T. Weymuth, M. Bensberg, K.-S. Csizi, M. Mörchen, P. L. Türtscher, M. Reiher,
"Heron: Visualizing and Controlling Chemical Reaction Explorations and Networks", **2024**, arXiv:2406.09541 [physics.chem-ph]
(DOI: 10.48550/arXiv.2406.09541).

Specific features which are implemented in or accessible via Heron are described in their
own papers. We kindly ask you to :doc:`cite these papers when appropriate <citing>`.

Additionally, we kindly request you to cite the corresponding software releases of the underlying SCINE modules
as archived on Zenodo.

Furthermore, when publishing results obtained with any SCINE module, please cite the following paper:

T. Weymuth, J. P. Unsleber, P. L. Türtscher, M. Steiner, J.-G. Sobez, C. H. Müller, M. Mörchen,
V. Klasovita, S. A. Grimmel, M. Eckhoff, K.-S. Csizi, F. Bosia, M. Bensberg, M. Reiher,
"SCINE—Software for chemical interaction networks", *J. Chem. Phys.*, **2024**, *160*, 222501
(DOI `10.1063/5.0206974 <https://doi.org/10.1063/5.0206974>`_).

Known Issues
------------

- The selection of nuclei is broken for vtk>=9.1, we therefore encourage to stay with version 9.0. This version is not available for python>=3.9 on PyPI and requires a manual install.
- Old versions of qt-material may cause overlapping text boxes for newer operating systems such as Ubuntu 22.04.
- An install of PySide2 via PyPI may not be sufficient to have a working Qt installation depending on your system. In this case, it is recommend to first install PySide2 with a package manager (such as apt) before installing it with pip.
- Some PySide2 packages might require additional installs related to pulseaudio such as `libpulse-mainloop-glib0`
- The start of a steered exploration can become quite slow (\~10 seconds) once the protocol gets large (> 20 steps) and issues can occur if you add a new step and immediately start the exploration or start the exploration and immediately click other buttons. Please do not click anything shortly after progressing the protocol. We hope to resolve this by the next release.

Support and Contact
-------------------

In case you should encounter problems or bugs, please write a short message
to scine@phys.chem.ethz.ch.
