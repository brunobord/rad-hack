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
import yaml


HTACCESS = """
# Serving .md files as UTF-8.
AddType 'text/plain; charset=UTF-8' md
""".strip()
SOURCE_FILE_TEXT = '<p><a href="{source_file}">Link to {source_file_basename}</a></p>'  # noqa
DEFAULT_PAGE = {}


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
        self.meta = {}

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

    def load_meta(self, language):
        "Update meta information dictionary"
        # Search for meta
        filepath = join(self.source_path, language, 'meta.yaml')
        if os.path.exists(filepath):
            with open(filepath) as fd:
                content = fd.read()
            self.meta[language] = yaml.load(content)

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

    def get_item_homepage(self, language, page):
        label = page.get('label', 'RAD-Hack')
        item = '* [{label}]({language}/{target})'.format(
            label=label,
            language=language,
            target='index.html',
        )

        # Add optional author
        author = page.get('author', None)
        if author:
            item = '{}, by {}'.format(item, author)

        # Add optional version
        version = page.get('version', None)
        if version:
            item = '{} (v{})'.format(item, version)

        # Add link to source
        item = '{item} ([source]({language}/{filename}))'.format(
            item=item,
            language=language,
            filename='rad-hack.md',
        )

        return item

    def build_home_text_list(self):
        "Build the full text list for the homepage"
        # Build text list
        text_list = []
        text_list.append('')
        for language in self.language_list:
            label = language
            meta_language = self.meta.get(language, {})
            label = meta_language.get('label', label)
            text_list.append('### {}'.format(label))
            for page in meta_language.get('pages', [DEFAULT_PAGE]):
                item = self.get_item_homepage(language, page)
                text_list.append(item)
        text_list.append('')
        return text_list

    def build_home(self):
        "Build the homepage"
        home_path = join(self.source_path, 'index.md')
        home_template = self.get_template(home_path)
        text_list = self.build_home_text_list()
        home_md = home_template.substitute(
            text_list='\n'.join(text_list),
        )
        home_html = convert_md_source(home_md)
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

    def build_language(self, language):
        source = join(self.source_path, language, 'rad-hack.md')
        target_dir = join(self.build_path, language)
        target_path = join(target_dir, 'index.html')
        # Create directory if needed
        self.mkdir(target_dir)
        page_html = self.convert_md(source)
        self.write_html(
            target_path,
            body=page_html,
            title=self.meta[language]['label'],
            prefix="../",
        )
        # Copy source
        shutil.copyfile(source, join(target_dir, 'rad-hack.md'))

    @cached_property
    def language_list(self):
        dir_list = os.listdir(self.source_path)
        dir_list = map(lambda x: join(self.source_path, x), dir_list)
        dir_list = filter(lambda x: os.path.isdir(x), dir_list)
        dir_list = map(lambda x: basename(x), dir_list)
        return list(dir_list)

    def build(self):
        self.mkdir(self.build_path)
        # Copy static paths
        if os.path.isdir(self.static_path):
            shutil.rmtree(self.static_path)
        shutil.copytree('static', self.static_path)
        # Write an .htaccess file
        with open(join(self.build_path, '.htaccess'), 'w') as fd:
            fd.write(HTACCESS)

        # Build every language
        for language in self.language_list:
            self.load_meta(language)
            self.build_language(language)

        # -- Build pages --
        # Index build
        self.build_home()
        # License page build
        self.build_license()
