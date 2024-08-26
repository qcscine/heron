from pathlib import Path
#import subprocess
#import sys
#
#class get_pybind_include(object):
#    """Helper class to determine the pybind11 include path
#
#    The purpose of this class is to postpone importing pybind11
#    until it is actually installed, so that the ``get_include()``
#    method can be invoked. """
#
#    def __init__(self, user=False):
#        try:
#            import pybind11
#        except ImportError:
#            if subprocess.call([sys.executable, '-m', 'pip', 'install', 'pybind11', "--user"]):
#                raise RuntimeError('pybind11 install failed.')
#
#        self.user = user
#
#    def __str__(self):
#        import pybind11
#        return pybind11.get_include(self.user)

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
    author="ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group",
    author_email="scine@phys.chem.ethz.ch",
    description="Connect OpenHaptics to the SCINE UI.",
    ext_modules=[openhaptics_module],
    cmdclass={"build_ext": build_ext},
)
