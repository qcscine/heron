from pathlib import Path

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

openhaptics_module = Pybind11Extension(
    "scine_heron_haptic",
    [str(fname) for fname in Path("src").glob("*.cpp")],
    include_dirs=["include"],
    extra_compile_args=["-W", "-O2", "-Dlinux"],
    extra_link_args=["-lHDU", "-lHD"]
)

setup(
    name="scine_heron_haptic",
    version=1.0,
    author="ETH Zurich, Laboratory of Physical Chemistry, Reiher Group",
    author_email="scine@phys.chem.ethz.ch",
    description="Connect OpenHaptics to the SCINE UI.",
    ext_modules=[openhaptics_module],
    cmdclass={"build_ext": build_ext},
)
