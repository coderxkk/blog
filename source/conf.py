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
html_static_path = ["_static"]
html_css_files = ["home.css"]

blog_baseurl = "https://coderxkk.github.io/blog/"
blog_path = "posts"
blog_post_pattern = "posts/*.rst"

html_sidebars = {
    "index": [],
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
    "navbar_center": [],
    "external_links": [
        {
            "name": "github主页",
            "url": "https://github.com/coderxkk"
        }
    ]
}

# 在 conf.py 文件末尾添加
def setup(app):
    # 在构建完成后自动创建 .nojekyll 文件
    app.connect('build-finished', create_nojekyll)

def create_nojekyll(app, exception):
    if exception is None:
        import os
        nojekyll_path = os.path.join(app.outdir, '.nojekyll')
        with open(nojekyll_path, 'w') as f:
            pass  # 创建空文件
        print(f"Created {nojekyll_path}")
