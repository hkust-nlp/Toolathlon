from setuptools import setup, Extension
from Cython.Build import cythonize

# Let Cython find and compile your .py files directly.
# This compiles both __init__.py and benchmark_utils.py

extensions = [
    Extension("utils.__init__", ["utils/__init__.py"]),
    Extension("utils.benchmark_utils", ["utils/benchmark_utils.py"]),
]

setup(
    name="my_utils_package",
    ext_modules=cythonize(
        extensions,
        # Tell Cython you're using Python 3 syntax
        compiler_directives={'language_level' : "3"}
    )
)
