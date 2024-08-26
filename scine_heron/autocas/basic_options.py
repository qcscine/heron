__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from enum import Enum


class Interfaces(Enum):

    OpenMolcas = "OpenMolcas"
    Serenity = "Serenity"


class BasicOptions:
    def __init__(self):
        self.interface = Interfaces.OpenMolcas
        self.basis_set: str = "cc-pvdz"
        self.charge: int = 0
        self.spin_multiplicity: int = 0
        self.number_of_roots: int = 1
        self.error_message: str = ""
