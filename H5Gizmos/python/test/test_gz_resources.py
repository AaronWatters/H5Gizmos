
# Requires python 3.8
# Run from setup folder:
# nosetests --with-coverage --cover-html --cover-package=H5Gizmos --cover-erase --cover-inclusive

import unittest
import os

from H5Gizmos.python.gz_resources import (
    HTMLPage,
    Resource,
    get_file_path,
)

class TestHTMLGeneration(unittest.TestCase):

    def test_remote_and_embedded_js(self):
        P = HTMLPage(title="abc123", embed_gizmo=False)
        css_url = "https://www.unpkg.com/browse/css-layout@1.1.1/dist/css-layout.css"
        js_url = "https://unpkg.com/wavesurfer.js"
        script_code = "element.wavesurfer.load(url);"
        P.remote_css(css_url)
        P.remote_js(js_url)
        P.embedded_script(script_code)
        S = P.as_string()
        #print("HTML")
        #print(S)
        self.assertIn(css_url, S)
        #self.assertEqual(1, 9)

    def test_defaults(self):
        R = Resource()
        # for coverage
        self.assertIsNone(R.html_embedding())
        # this method is commented for now
        #self.assertIsNone(R.configure_in_gizmo_manager())


class TestFileNames(unittest.TestCase):

    def test_finds_local_test_file_folder(self):
        path = "./files_for_testing"
        full_path = get_file_path(path)
        assert os.path.isdir(full_path)
        assert os.path.isfile(os.path.join(full_path, "example.file"))

    def test_finds_module_relative_file(self):
        path = "../../H5Gizmos/python"
        full_path = get_file_path(path)
        assert os.path.isdir(full_path)
        assert os.path.isfile(os.path.join(full_path, "hex_codec.py"))

    def test_finds_other_module_relative_file(self):
        import asyncio
        path = "./futures.py"  # may break if structure changes
        full_path = get_file_path(path, relative_to_module=asyncio)
        #self.assertEqual(full_path, None)
        assert os.path.isfile(full_path)

    def test_finds_js_source(self):
        path = "../../H5Gizmos/js/H5Gizmos.js"
        full_path = get_file_path(path, local=False)
        content = open(full_path).read()
        self.assertIn("Gizmo protocol.", content)
