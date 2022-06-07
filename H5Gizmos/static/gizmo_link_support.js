
// The URL prefix for links
var url_prefix = null;

// for debugging
var json_data = null;

function setup_start_page(json_parameters) {
    debugger;
    json_data = json_parameters;
    // Determine the fully specified URL prefix
    var location = window.location;
    url_prefix = location.origin + location.pathname;
    var textarea_info = "export GIZMO_LINK_PREFIX=" + url_prefix
    $('#gizmo_link_prefix').val(textarea_info);
    var list_area = $("#gizmo_script_list");
    var module_name = json_parameters.module_name;
    var script_name = json_parameters.script_name;
    if (!module_name) {
        // list all module info short description.
        modules_and_scripts = json_parameters.modules_and_scripts;
        if ( (modules_and_scripts) && (modules_and_scripts.length > 0)) {
            for (var i=0; i<modules_and_scripts.length; i++) {
                var [module_name, scripts] = modules_and_scripts[i];
                var emodule = encodeURIComponent(module_name);
                var mlink = `${url_prefix}?module=${emodule}`
                var module_tag = `<h3 title="show details"> <a href=${mlink}>${module_name}</a> </h3>`;
                $(module_tag).appendTo(list_area);
                for (var j=0; j<scripts.length; j++) {
                    script_name = scripts[j];
                    slink = `${mlink}&script=${script_name}`
                    var script_tag = `<h4 title="start script"> <a href="${slink}">${script_name}</a> </h4>`;
                    $(script_tag).appendTo(list_area);
                }
            }
        } else {
            list_area.html("No modules with registered gizmo scripts found.")
        }
    } else if (!script_name) {
        // list details for module
        list_area.html(`module=${module_name}`);
    } else {
        // redirect to start script
        list_area.html(`module=${module_name}; script=${script_name}`);
    }
};