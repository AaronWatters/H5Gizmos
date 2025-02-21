"""
Utilities for launching Gizmo scripts using entry point annotations.
"""

from operator import mod
#import pkg_resources

ENTRY_POINT_GROUP_NAME = "H5Gizmos.scripts"

GIZMO_SCRIPT = "gizmo_script"

module_to_name_to_entry = {}

def find_entry_points():
    import pkg_resources
    if len(module_to_name_to_entry) == 0:
        for entry in pkg_resources.iter_entry_points(group=ENTRY_POINT_GROUP_NAME):
            entry_name = entry.name
            entry_full_module = entry.module_name
            entry_module = entry_full_module.split(".")[0]
            name_to_entry = module_to_name_to_entry.get(entry_module, {})
            name_to_entry[entry_name] = entry
            module_to_name_to_entry[entry_module] = name_to_entry
    return module_to_name_to_entry

def main():
    import sys
    args = sys.argv
    nargs = len(args)
    assert nargs > 0, "no arguments??"
    if nargs == 1:
        find_entry_points()
        print("The following packages advertise", ENTRY_POINT_GROUP_NAME, "entry points")
        print()
        for module_name in sorted(module_to_name_to_entry.keys()):
            print(GIZMO_SCRIPT, module_name)
        return
    else:
        assert nargs == 2, "Only one argument expected: " + repr(args)
        arg = args[1]
        split_args = arg.split("/")
        if len(split_args) == 1:
            list_entry_points(arg)
            return
        else:
            [module_name, script_name] = split_args
            start_entry_point(module_name, script_name)

def list_entry_points(module_name):
    import importlib
    the_module = importlib.import_module(module_name)
    print(repr(ENTRY_POINT_GROUP_NAME), "entry points for", repr(module_name))
    print()
    doc = the_module.__doc__
    if doc is not None:
        print("Package documentation string:")
        print(doc)
        print()
    find_entry_points()
    name_to_entry = module_to_name_to_entry.get(module_name, {})
    print(len(name_to_entry), "entry points:")
    for name in sorted(name_to_entry.keys()):
        entry = name_to_entry[name]
        print()
        print(GIZMO_SCRIPT, module_name + "/" + name)
        loaded = entry.load()
        if hasattr(loaded, "__doc__"):
            entry_doc = loaded.__doc__
            if entry_doc is not None:
                print("    " + entry_doc)
                print()

def modules_and_scripts_json():
    # xxx refactor above...
    find_entry_points()
    result = []
    for module_name in sorted(module_to_name_to_entry.keys()):
        name_to_entry = module_to_name_to_entry[module_name]
        script_names = list(sorted(name_to_entry.keys()))
        result.append([module_name, script_names])
    return result

def module_detail_json(module_name):
    import importlib
    # xxx refactor above...
    find_entry_points()
    result = dict(name=module_name)
    script_list = result["script_list"] = []
    result["script_info"] = "Module %s has no registered gizmo entry points." % repr(module_name)
    try:
        the_module = importlib.import_module(module_name)
    except Exception as e:
        result["module_doc"] = "Could not import %s: %s" % (module_name, e)
    else:
        result["module_doc"] = the_module.__doc__
        name_to_entry = module_to_name_to_entry.get(module_name, None)
        if name_to_entry:
            result["script_info"] = (
                "Module %s has %s registered gizmo entry points." 
                % (repr(module_name), len(name_to_entry))
            )
            for name in sorted(name_to_entry.keys()):
                entry = name_to_entry[name]
                loaded = entry.load()
                doc = getattr(loaded, "__doc__", None)
                script_info = dict(
                    name=name,
                    doc=doc,
                )
                script_list.append(script_info)
    return result

def start_entry_point(module_name, script_name):
    find_entry_points()
    name_to_entry = module_to_name_to_entry[module_name]
    entry = name_to_entry[script_name]
    loaded = entry.load()
    return loaded()

