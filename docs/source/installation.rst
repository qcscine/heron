Installation
------------

.. inclusion-marker-do-not-remove

Preliminary Remark
..................

The application requires several third-party and SCINE Python packages to run.
Due to the modular nature of SCINE, we do not enforce all individual modules to be installed in order to launch Heron.
Depending on the installed software packages some features are available or missing.
We provide easy installs for all possible combinations of requirements.

The hard requirements for Heron are:

  - SCINE Sparrow
  - SCINE ReaDuct
  - SCINE Utilities

The optional requirements are:

  - SCINE Chemoton
  - SCINE Database
  - SCINE Art
  - SCINE Molassembler
  - SCINE Swoose
  - SCINE autoCAS
  
Additional optional requirements are modules that add further backend programs to our framework, which are:

  - SCINE xtb_wrapper
  - SCINE serenity_wrapper

From PyPI
.........

Heron can be installed from PyPI with the command::

  pip install scine-heron

This will install only the hard requirements (see above), and hence only a minimal version of
Heron will be available. To install all dependencies, run::

  pip install scine-heron[all]

If you want to install only selected dependencies, you can run a command such as::

  pip install scine-heron[autocas]

On PyPI, we also support any possible combination of optional dependencies combined with a ``+`` such as::

  pip install scine-heron[autocas+chemoton]

From Source
...........

Heron can be installed using pip (pip3) once the repository has been cloned:

.. code-block:: bash

   git clone https://github.com/qcscine/heron.git
   cd heron
   pip install -r requirements.txt
   pip install .

A non super user can install the package using a virtual environment, or the ``--user`` flag.

Only the hard requirements (see above) are included in ``requirements.txt``. If all optional
requirements are wanted, one can install them after cloning with::

  pip install -r requirements-all.txt

If one wants to install only certain optional requirements, one can install the specific
requirements file such as::

  pip install -r requirements-autocas.txt


