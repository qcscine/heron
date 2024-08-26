# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from os import path, walk
from itertools import combinations
from setuptools import setup, find_packages
import sys

min_version = (3, 6)
if sys.version_info < min_version:
    error = """
SCINE GUI does not support Python {0}.{1}.
Python {2}.{3} and above is required. Check your Python version like so:

python3 --version

This may be due to an out-of-date pip. Make sure you have pip >= 9.0.1.
Upgrade pip like so:

pip install --upgrade pip
""".format(
        *(sys.version_info[:2] + min_version)
    )
    sys.exit(error)

here = path.abspath(path.dirname(__file__))


def read_requirements(file_name: str):
    with open(path.join(here, file_name)) as requirements_file:
        # Parse requirements.txt, ignoring any commented-out lines.
        requirements = []
        for line in requirements_file:
            if line.startswith("#"):
                continue
            if line.startswith("-r"):
                requirements.extend(read_requirements(line.split()[-1].strip()))
            else:
                requirements.append(line.strip())
        return list(set(requirements))

variants = []
for subdir, dirs, files in walk(here):
    for f in files:
        if 'requirements-' in f:
            variants.append(f.split("requirements-")[-1].split(".txt")[0])

assert "all" in variants
assert "dev" in variants
variants.remove('all')
variants.remove('dev')
package_variants = {
    'all': read_requirements('requirements-all.txt')
}
variants_combinations = [["_".join(sorted(i)) for i in combinations(variants, len(variants) - j)]
                         for j in range(1, len(variants))]


def flatten_list(_list):
    return [item for sublist in _list for item in sublist]


flat_variants = flatten_list(variants_combinations)
for v in flat_variants:
    sub_variants = v.split("_")
    all_requirements = list(set(flatten_list(
        [read_requirements(f"requirements-{sub}.txt") for sub in sub_variants])))
    package_variants[v] = all_requirements

with open(path.join(here, "README.rst"), encoding="utf-8") as readme_file:
    readme = readme_file.read()

with open(path.join(here, 'scine_heron', '_version.py')) as f:
    exec(f.read())

# Define the setup
setup(
    name="scine_heron",
    version=__version__,
    author="ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group",
    author_email="scine@phys.chem.ethz.ch",
    description="Graphical user interface for SCINE",
    long_description=readme,
    url="https://www.scine.ethz.ch",
    python_requires=">={}".format(".".join(str(n) for n in min_version)),
    packages=find_packages(include=["scine_heron", "scine_heron.*"],
                           exclude=["scine_heron.tests*"]),
    include_package_data=True,
    package_data={
        "scine_heron": [
            "resources/*",
            "resources/icons/*",
            "resources/sounds/*",
            # When adding files here, remember to update MANIFEST.in as well,
            # or else they will not be included in the distribution on PyPI!
            # 'path/to/data_file',
        ]
    },
    license="BSD (3-clause)",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: C++",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Topic :: Scientific/Engineering :: Chemistry",
    ],
    entry_points={
        'console_scripts': [
            'scine_heron = scine_heron.__main__:main',
            'scine_heron_view_trajectory = scine_heron.__init__:view_trajectory_cli',
        ],
    },
    install_requires=read_requirements('requirements.txt'),
    extras_require=package_variants,
    zip_safe=False,
    test_suite="pytest",
    tests_require=read_requirements('requirements-all.txt'),
)
