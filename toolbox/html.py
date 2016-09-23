import os
from os.path import abspath, join, basename
from string import Template
import shutil

from cached_property import cached_property
import markdown
from markdown.extensions.toc import TocExtension
from mdx_gfm import GithubFlavoredMarkdownExtension
from slugify import slugify
from shell import shell


HTACCESS = """
# Serving .md files as UTF-8.
AddType 'text/plain; charset=UTF-8' md
""".strip()
SOURCE_FILE_TEXT = '<p><a href="{source_file}">Link to {source_file_basename}</a></p>'  # noqa


def convert_md_source(source):
    "Convert Markdown content into HTML"
    html = markdown.markdown(
        source,
        extensions=[
            GithubFlavoredMarkdownExtension(),
            TocExtension(permalink=True, slugify=slugify)
        ]
    )
    return html


class HTMLBuilder(object):

    def __init__(self):
        self.source_path = abspath(join('.', 'sources'))
        self.build_path = abspath(join('.', 'build'))
        self.static_path = join(self.build_path, 'static')
        self.main_template = self.get_template(join('templates', 'base.html'))

    def mkdir(self, path):
        "Silent make directories"
        if not os.path.isdir(path):
            os.makedirs(path)

    @cached_property
    def version(self):
        return shell('git describe --tags --abbrev=0').output(raw=True).strip()

    @cached_property
    def git_version(self):
        return shell('git describe --tags').output(raw=True).strip()

    def get_template(self, path):
        "Transform a path into a template"
        with open(path) as fd:
            template_string = fd.read()
        template = Template(template_string)
        return template

    def convert_md(self, filepath):
        "Convert a Markdown file into HTML"
        with open(filepath) as fd:
            source = fd.read()
        return convert_md_source(source)

    def write_html(self, target_filepath, body, title,
                   prefix='', source_file=''):
        "Write HTML page (body & title) in the target_filepath"
        if source_file:
            source_file_basename = basename(source_file)
            source_file = SOURCE_FILE_TEXT.format(
                source_file=source_file,
                source_file_basename=source_file_basename
            )
        html = self.main_template.substitute(
            body=body,
            title=title,
            static=prefix + 'static',
            license=prefix + 'license.html',
            version=self.version,
            git_version=self.git_version,
            source_file=source_file,
        )
        with open(target_filepath, 'w') as fd:
            fd.write(html)

    def build_home(self):
        "Build the homepage"
        home_html = self.convert_md(join(self.source_path, 'index.md'))
        self.write_html(
            join(self.build_path, 'index.html'),
            body=home_html,
            title="Home",
        )

    def build_license(self):
        "Build License page"
        license_html = self.convert_md('LICENSE')
        self.write_html(
            join(self.build_path, 'license.html'),
            body=license_html,
            title="Open Gaming License",
        )

    def build(self):
        self.mkdir(self.build_path)
        # Copy static paths
        if os.path.isdir(self.static_path):
            shutil.rmtree(self.static_path)
        shutil.copytree('static', self.static_path)
        # Write an .htaccess file
        with open(join(self.build_path, '.htaccess'), 'w') as fd:
            fd.write(HTACCESS)

        # -- Build pages --
        # Index build
        self.build_home()
        # License page build
        self.build_license()
