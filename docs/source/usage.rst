Usage
------

.. inclusion-marker-do-not-remove

Starting the Application
........................

The application can be started by the command::

    python3 -m scine_heron

To open a file with a molecule directly from the command line, you can use the ``--file`` option::

    python3 -m scine_heron --file examples/xyz_files/pyridine.xyz

To specify a certain method family and/or program for interactive calculations directly from the command line, you can use the ``--method-family`` 
and ``--program`` options::

    python3 -m scine_heron --method-family DFTB3 --program Sparrow

Hybrid models can be specified by combining two method families and programs with a ``/`` character, such as::

    python3 -m scine_heron --method-family DFTB3/SFAM --program Sparrow/Swoose

To specify a database connection directly from the command line, you can use the ``--name``, ``--ip``, and ``--port`` options
and optionally try to connect with the database upon launch with the ``--connect`` flag::

    python3 -m scine_heron --name test_database --ip localhost --port 27017 --connect

The application is per default in dark mode. If light mode is preferred, you can use the ``--mode`` option::

    python3 -m scine_heron --mode light

A summary of all command line arguments and short forms is given by::

    python3 -m scine_heron --help

Shortcuts
.........

The application features a range of shortcuts. The most important ones are given here.

General:
 - Scrolling Vertically: Mouse Wheel
 - Scrolling Vertically: Shift + Mouse Wheel
 - Zooming: Ctrl + Mouse Wheel (in the main molecular viewer also without Ctrl modifier)
 - Open Database Connection Dialogue: Ctrl + D
 - Open Reaction Template database: Ctrl + T

Main Molecular Viewer:
 - Open File: Ctrl + O
 - Save Molecule: Ctrl + S
 - Save Trajectory: Ctrl + Shift + S
 - Start Real Time Calculation: Ctrl + F (if calculator is available and molecule loaded)
 - Select multiple atoms: s + Right Click
 - Undo changes in the interactive setting: Ctrl + Z
 - Move the current structure to ReaDuct: Ctrl + R

All Network Views:
  - Copy ID of Focussed Node: Ctrl + C

Existing shortcuts are usually given in the mouse-over tooltip of the particular buttons in Heron.

AutoCAS
.......

In order to set up/analyze an AutoCAS project, the ``scine-autocas`` module must be installed, see prerequisites.
Since the autoCAS project is still under development, it could be that a newer version of autoCAS may break this
version of SCINE Heron.
In order to use the autoCAS GUI here, ensure that you use the exact autoCAS version ``v2.1.0``.
In order to use autoCAS you need to have Molcas installed.
Please see the `autoCAS readme <https://github.com/qcscine/autocas/blob/master/README.rst>`_ for installation instructions.

Database and Chemoton
.....................

The SCINE Database and automated exploration with SCINE Chemoton is built around the general MongoDB database.
MongoDB is a document-based database format, which allows one to store heterogeneous data. SCINE database defines a database
schema and offers C++ and Python functionalities to query relevant information.
To run a SCINE Database one first needs to install the MongoDB client, which is freely available and installable with
most package managers. Detailled instructions are given in the `MongoDB documentation <https://www.mongodb.com/docs/manual/installation/>`_.


