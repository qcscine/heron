#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Testing of MoldenFileReader.
"""

from scine_heron.electronic_data.molden_file_reader import MoldenFileReader


def molden_data() -> str:
    return (
        "[Molden Format]\n"
        "This is a test data, NOT real. Real file is too big.\n"
        "[Atoms] (AU)\n"
        "C    1         6                6.1052194517       1.7410254664       1.1040800477\n"
        "C    2         6                4.1377462140       3.8156688521       0.6563037731\n"
        "[GTO]\n"
        "1 0\n"
        "s    6    1.00\n"
        "116.0690322429      -0.1046234805\n"
        "21.2858804144      -0.1459904193\n"
        "5.9817916163      -0.1403997584\n"
        "0.8554094819       0.2121298425\n"
        "0.3882374328       0.1970386706\n"
        "0.1851482379       0.0344592482\n"
        "p    6    1.00\n"
        "17.0160777741       0.3903657330\n"
        "4.4374470513       0.4722439228\n"
        "1.5877608354       0.4822910285\n"
        "0.6637143790       0.3458254681\n"
        "0.3034954267       0.1288339964\n"
        "0.1434819294       0.0132401392\n"
        "\n"
        "2 0\n"
        "s    6    1.00\n"
        "156.8722084896      -0.1311448979\n"
        "28.7687680834      -0.1829981046\n"
        "8.0846444865      -0.1759902450\n"
        "1.1561221111       0.2659034700\n"
        "0.5247193186       0.2469867777\n"
        "0.2502356779       0.0431944585\n"
        "p    6    1.00\n"
        "23.4554482379       0.5830449406\n"
        "6.1167039198       0.7053370895\n"
        "2.1886149431       0.7203433097\n"
        "0.9148828812       0.5165202079\n"
        "0.4183467757       0.1924247019\n"
        "0.1977795949       0.0197752916\n"
        "\n"
        "[5D]\n"
        "[7F]\n"
        "[9G]\n"
        "[MO]\n"
        "Sym=      A1\n"
        "Ene=      -1.2930088102\n"
        "Spin=     Alpha\n"
        "Occup=    2.0\n"
        "1     -0.1478707692\n"
        "2      0.0749600266\n"
        "3      0.0300591731\n"
        "4      0.0143911533\n"
        "5     -0.1404540814\n"
        "Sym=      A1\n"
        "Ene=      -1.1541558820\n"
        "Spin=     Alpha\n"
        "Occup=    2.0\n"
        "1     -0.1033714030\n"
        "2      0.0269856136\n"
        "3      0.0093981120\n"
        "4      0.0033493253\n"
        "5     -0.0829585455\n"
    )


def test_reader() -> None:
    mr = MoldenFileReader()
    electronic_data = mr.read_molden(molden_data())

    assert len(electronic_data.atoms) == 2

    assert electronic_data.atoms[0].name == "C"
    assert electronic_data.atoms[0].elem == 6
    assert electronic_data.atoms[0].coordinates == [
        3.230742999978833,
        0.9213110000149878,
        0.5842539999982865,
    ]

    assert electronic_data.atoms[1].name == "C"
    assert electronic_data.atoms[1].elem == 6
    assert electronic_data.atoms[1].coordinates == [
        2.1896009999848727,
        2.0191649999946786,
        0.3473010000012546,
    ]

    assert len(electronic_data.mo) == 2

    mo0 = electronic_data.mo[0]
    mo1 = electronic_data.mo[1]

    assert mo0.symmetry == "A1"
    assert mo0.energy == -1.2930088102
    assert mo0.spin == "Alpha"
    assert mo0.occupation == 2.0
    assert len(mo0.coefficients) == 5
    assert all(
        [
            abs(a - b) <= 0.0001
            for a, b in zip(
                mo0.coefficients,
                [
                    -0.1478707692,
                    0.0749600266,
                    0.0300591731,
                    0.0143911533,
                    -0.1404540814,
                ],
            )
        ]
    )

    assert mo1.symmetry == "A1"
    assert mo1.energy == -1.1541558820
    assert mo1.spin == "Alpha"
    assert mo1.occupation == 2.0
    assert len(mo1.coefficients) == 5
    assert all(
        [
            abs(a - b) <= 0.0001
            for a, b in zip(
                mo1.coefficients,
                [
                    -0.1033714030,
                    0.0269856136,
                    0.0093981120,
                    0.0033493253,
                    -0.0829585455,
                ],
            )
        ]
    )

    go0 = electronic_data.atoms[0].gaussian_orbitals[0]
    assert go0.orb_type == "s"

    assert go0.nr_gaussians == 6
    assert go0.coefficients[0] == [116.0690322429, -0.1046234805]
    assert go0.coefficients[1] == [21.2858804144, -0.1459904193]
    assert go0.coefficients[2] == [5.9817916163, -0.1403997584]
    assert go0.coefficients[3] == [0.8554094819, 0.2121298425]
    assert go0.coefficients[4] == [0.3882374328, 0.1970386706]
    assert go0.coefficients[5] == [0.1851482379, 0.0344592482]

    go1 = electronic_data.atoms[0].gaussian_orbitals[1]
    assert go1.orb_type == "p"

    assert go1.nr_gaussians == 6
    assert go1.coefficients[0] == [17.0160777741, 0.3903657330]
    assert go1.coefficients[1] == [4.4374470513, 0.4722439228]
    assert go1.coefficients[2] == [1.5877608354, 0.4822910285]
    assert go1.coefficients[3] == [0.6637143790, 0.3458254681]
    assert go1.coefficients[4] == [0.3034954267, 0.1288339964]
    assert go1.coefficients[5] == [0.1434819294, 0.0132401392]

    go0 = electronic_data.atoms[1].gaussian_orbitals[0]
    assert go0.orb_type == "s"

    assert go0.nr_gaussians == 6
    assert go0.coefficients[0] == [156.8722084896, -0.1311448979]
    assert go0.coefficients[1] == [28.7687680834, -0.1829981046]
    assert go0.coefficients[2] == [8.0846444865, -0.1759902450]
    assert go0.coefficients[3] == [1.1561221111, 0.2659034700]
    assert go0.coefficients[4] == [0.5247193186, 0.2469867777]
    assert go0.coefficients[5] == [0.2502356779, 0.0431944585]

    go1 = electronic_data.atoms[1].gaussian_orbitals[1]
    assert go1.orb_type == "p"

    assert go1.nr_gaussians == 6
    assert go1.coefficients[0] == [23.4554482379, 0.5830449406]
    assert go1.coefficients[1] == [6.1167039198, 0.7053370895]
    assert go1.coefficients[2] == [2.1886149431, 0.7203433097]
    assert go1.coefficients[3] == [0.9148828812, 0.5165202079]
    assert go1.coefficients[4] == [0.4183467757, 0.1924247019]
    assert go1.coefficients[5] == [0.1977795949, 0.0197752916]
