# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import ablog
import pydata_sphinx_theme
project = 'koi-blogs'
copyright = '2026, zekun.wang'
author = 'zekun.wang'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'ablog',
    'sphinx.ext.intersphinx',
]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"

blog_baseurl = ""
blog_path = "posts"
blog_post_pattern = "posts/*.rst"

html_sidebars = {
    "**": [
        "sidebar-nav-bs",
        "ablog/recentposts.html",
        "ablog/tagcloud.html",
        "ablog/categories.html",
        "ablog/archives.html",
        "search-field.html"
    ]
}

suppress_warnings = [
    "toc.not_included",
]

html_theme_options = {
    "external_links": [
        {
            "name": "github主页",
            "url": "https://github.com/coderxkk"
        }
    ]
}