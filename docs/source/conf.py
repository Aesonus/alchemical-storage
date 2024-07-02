# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

import alchemical_storage

project = "Alchemical Storage"
copyright = "2023, Cory Laughlin (Aesonus)"
author = "Cory Laughlin (Aesonus)"
release = alchemical_storage.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "m2r2",
]

templates_path = ["_templates"]
exclude_patterns = []

sys.path.insert(0, os.path.abspath("../.."))


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]
html_theme_options = {
    "fixed_sidebar": True,
    "description": "A package to bridge CRUD operations with SQLAlchemy query constructs.",
}
