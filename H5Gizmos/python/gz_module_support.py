
"""
Support for Javascript ES6 modules and NPM based installation.
"""

import json
import os
from urllib.parse import urljoin

IMPORT_MAP_FORMAT = """
<script type="importmap">
{import_map_json:s}
</script>
"""

MODULE_LOADER_SCRIPT_FORMAT = """
<script type="module">
  // load modules
  {star_imports:s}
  //console.log("loaded", qd_vector.name);
  function initialize_modules() {{
      const tr = window.H5GIZMO_INTERFACE;
      // record module references
      {set_references:s}
  }};
  window.addEventListener("load", initialize_modules, true);
  // H5GIZMO_INTERFACE.object_cache.qd_vector.name -> 'qd_vector'
</script>
"""

class Module_context:

    def __init__(self):
        self.import_mapping = {}
        self.parameter_to_identifier = {}

    def load_module(self, parameter, identifier=None):
        if identifier is None:
            identifier = parameter
        self.parameter_to_identifier[parameter] = identifier

    def add_import_mapping(self, identifier, location):
        self.import_mapping[identifier] = location

    def map_node_modules(self, node_modules_folder, url_prefix="./node_modules", module_file_path=None):
        """
        Look for package.json entries in subfolders of node_modules_folder.
        Add import mapping for modules found.
        """
        # should refactor copied from _serve_folder and elsewhere... xxxx
        if module_file_path is not None:
            from_folder = os.path.dirname(module_file_path)
            abs_os_path0 = os.path.join(from_folder, node_modules_folder)
            node_modules_folder = os.path.abspath(abs_os_path0)
        assert os.path.isdir(node_modules_folder), "not a dir: " + repr(node_modules_folder)
        if not url_prefix.startswith("./"):
            url_prefix = "./" + url_prefix
        for fn in os.listdir(node_modules_folder):
            json_fn = os.path.join(node_modules_folder, fn, "package.json")
            if os.path.isfile(json_fn):
                module_url = os.path.join(url_prefix, fn) + "/"
                json_descriptor = json.load(open(json_fn))
                (name, mapping) = map_package_descriptor(json_descriptor)
                # ignore anything not of type module
                if (json_descriptor.get("type") == "module") or (json_descriptor.get("module")):
                    # (name, mapping) = map_package_descriptor(json_descriptor)
                    for (relative_link, entry_point) in mapping.items():
                        if relative_link == ".":
                            # module main entry point.
                            #print((module_url, entry_point))
                            url = os.path.join(module_url, entry_point).replace("\\","/")
                            #print(url)
                            url = url.replace("/./", "/") # eliminate trivial dots
                            self.add_import_mapping(name, url)
                        else:
                            pass  # other cases not yet implemented...

    def module_loader_html(self):
        p2i = self.parameter_to_identifier
        star_imports = []
        set_references = []
        for (param, identifier) in sorted(p2i.items()):
            star_import =  "\n  import * as %s from %s;" % (identifier, repr(param))
            star_imports.append(star_import)
            set_reference = "\n      tr.modules[%s] = %s" % (repr(identifier), identifier)
            #set_reference = "\n      tr.set_reference(%s, %s);" % (repr(identifier), identifier)
            set_references.append(set_reference)
        return MODULE_LOADER_SCRIPT_FORMAT.format(
            star_imports="\n".join(star_imports),
            set_references="\n".join(set_references),
        )

    def get_import_map_json(self):
        return {"imports": self.import_mapping}
    
    def import_map_html(self):
        json_ob = self.get_import_map_json()
        json_str = json.dumps(json_ob, indent=4)
        return IMPORT_MAP_FORMAT.format(import_map_json=json_str)
    
def map_package_descriptor(descriptor):
    name = descriptor["name"]
    # For now just look for "main" or "module" top level entries
    # Based on three.js example.
    # Other imports/exports not yet:
    # https://github.com/jkrems/proposal-pkg-exports/
    entry = descriptor.get("main")
    entry = descriptor.get("module", entry)
    mapping = {".":  entry}
    return (name, mapping)

def smoke_test():
    M = Module_context()
    M.add_import_mapping("qd_vector", "./node_modules/qd_vector/lib/index.js")
    M.load_module("qd_vector")
    print(M.import_map_html())
    print(M.module_loader_html())

def local_test0():
    # temporary
    folder = "/Users/awatters/test/importmap/qd_import/node_modules"
    M = Module_context()
    M.map_node_modules(folder)
    print(M.import_map_html())
    #print(M.module_loader_html())


if __name__ == "__main__":
    #smoke_test()
    local_test0()

