from __future__ import unicode_literals, print_function
import codecs
import os
import shutil
import tempfile
from bs4 import BeautifulSoup
from general_tools.file_utils import write_file, load_json_object
from general_tools.url_utils import join_url_parts, get_url


class Templater(object):
    def __init__(self, source_dir, output_dir, template_file, quiet):
        self.source_dir = source_dir  # Local directory
        self.output_dir = output_dir  # Local directory
        self.template_file = template_file  # Local file of template
        self.quiet = quiet

        self.files = sorted(glob(os.path.join(self.source_dir, '*.html')))
        self.manifest = {}
        self.template_html = ''

    def run(self):
        # get manifest.json
        with open(os.path.join(self.source_dir, 'manifest.json')) as manifest_file:
            self.manifest = json.load(manifest_file)

        with open(self.template_file) as template_file:
            self.template_html = template_file.read()

        self.apply_template()

    def build_left_sidebar(self):
        html = self.build_page_nav()
        html += '<div><h1>Revisions</h1><table width="100%" id="revisions"></table></div>'
        return html

    def build_page_nav(self):
        html = '<select id="page-nav" onchange="window.location.href=this.value">'
        for filename in self.files:
            name = os.path.splittext(filename)[0]
            html += '<option value="{0}">{1}</option>'.format(filename, name)
        html += '</select>'
        return html

    def apply_template(self):
        language_code = self.manifest['language']['slug']
        heading = '{0}: {1}'.format(self.manifest['language']['name'], self.manifest['name'])
        title = ''
        canonical = ''

        # apply the template
        template = BeautifulSoup(self.template_html, 'html.parser')

        # find the target div in the template
        content_div = template.body.find('div', {'id': 'content'})
        if not content_div:
            raise Exception('No div tag with id "content" was found in the template')

        left_sidebar_html = self.build_left_sidebar()
        left_sidebar_div = template.body.find('div', {'id': 'left-sidebar'})
        if left_sidebar_div:
            left_sidebar_div.clear()
            left_sidebar_div.append(left_sidebar_html)

        # loop through the downloaded files
        for filename in self.files:
            if not self.quiet:
                print('Applying template to {0}.'.format(filename))

            # read the downloaded file into a dom abject
            with codecs.open(filename, 'r', 'utf-8-sig') as file:
                soup = BeautifulSoup(file, 'html.parser')

            # get the language code, if we haven't yet
            if not language_code:
                language_code = soup.html['lang']

            # get the title, if we haven't
            if not title:
                title = soup.head.title.text

            # get the canonical UTL, if we haven't
            if not canonical:
                links = template.head.select('link[rel="canonical"]')
                if len(links) == 1:
                    canonical = links[0]['href']

            # get the content div from the temp file
            soup_content = soup.body.find('div', {'id', 'content'})
            if not soup_content:
                raise Exception('No div tag with class "content" was found in {0}'.format(file_name))

            # insert new HTML into the template
            content_div.clear()
            content_div.append(soup_content)
            template.html['lang'] = language_code
            template.head.title.clear()
            template.head.title.append(header)
            for a_tag in template.body.select('a[rel="dct:source"]'):
                a_tag.clear()
                a_tag.append(title)

            # set the page heading
            heading_span = template.body.find('span', {'id': 'h1'})
            heading_span.clear()
            heading_span.append(heading)

            # get the html
            html = unicode(template)

            # update the canonical URL - it is in several different locations
            html = html.replace(canonical, canonical.replace('/templates/', '/{0}/'.format(language_code)))

            # write to output directory
            out_file = os.path.join(self.output_dir, os.path.basename(filename))

            if not self.quiet:
                print('Writing {0}.'.format(out_file))

            write_file(out_file, html.encode('ascii', 'xmlcharrefreplace'))

        index_file = os.path.join(self.output_dir, 'index.html')
        if not os.path.isfile(index_file):
            shutil.copyfile(os.path.join(self.output_dir, self.files[0]), index_file)


class ObsTemplater(Templater):
    def __init__(self, *args, **kwargs):
        super(ObsTemplater, self).__init__(*args, **kwargs)


class BibleTemplater(Templater):
    def __init__(self, *args, **kwargs):
        super(BibleTemplater, self).__init__(*args, **kwargs)
