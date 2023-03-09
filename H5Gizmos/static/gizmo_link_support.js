
// The URL prefix for links
var url_prefix = null;

// for debugging
var json_data = null;

function setup_start_page(json_parameters) {
    debugger;

    function redirect_to(href) {
        console.log("automatically redirecting to", href)
        window.location.replace(href);
    };

    json_data = json_parameters;
    // Determine the fully specified URL prefix
    var location = window.location;
    url_prefix = location.origin + location.pathname;
    var textarea_info = "export GIZMO_LINK_PREFIX=" + url_prefix
    var link_arg = "&prefix=" + encodeURIComponent(url_prefix)
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
                var mlink = `${url_prefix}?module=${emodule}${link_arg}`
                var module_tag = `<h3 title="show details"> <a href="${mlink}">${module_name}</a> </h3>`;
                $(module_tag).appendTo(list_area);
                var script_block = $("<blockquote/>").appendTo(list_area);
                for (var j=0; j<scripts.length; j++) {
                    script_name = scripts[j];
                    var escript = encodeURIComponent(script_name);
                    var slink = `${mlink}&script=${escript}`;
                    var script_tag = `<h4 title="start script"> <a href="${slink}" target="_blank" >${script_name}</a> </h4>`;
                    $(script_tag).appendTo(script_block);
                }
            }
        } else {
            list_area.html("No modules with registered gizmo scripts found.")
        }
    } else if (!script_name) {
        // list details for module
        //list_area.html(`module=${module_name}`);
        module_detail = json_parameters.module_detail;
        if (module_detail.module_doc) {
            $(`<h2>${module_name} description:</h2>`).appendTo(list_area);
            $(`<blockquote> <b> ${module_detail.module_doc} </b> </blockquote>`).appendTo(list_area);
        }
        $(`<h2>Gizmo scripts in ${module_name}</h2>`).appendTo(list_area);
        var script_info = module_detail.script_info;
        var script_list = module_detail.script_list;
        $(`<blockquote><em>${script_info}</em></blockquote>`).appendTo(list_area);
        for (var i=0; i<script_list.length; i++) {
            var script_detail = script_list[i];
            var script_name = script_detail.name;
            var script_doc = script_detail.doc;
            var emodule = encodeURIComponent(module_name);
            var escript = encodeURIComponent(script_name);
            var script_link = `${url_prefix}?module=${emodule}&script=${escript}${link_arg}`;
            $(`<h4><a href="${script_link}" target="_blank" >${script_name}</a></h4>`).appendTo(list_area);
            if (script_doc) {
                $(`<blockquote>${script_doc}</blockquote>`).appendTo(list_area);
            }
        }
    } else {
        // redirect to start script
        //list_area.html(`module=${module_name}; script=${script_name}`);
        var launch_exception = json_parameters.launch_exception;
        if (launch_exception) {
            list_area.html(`
                <div>
                    <h3>Failed to launch script</h3>
                    <blockquote> ${launch_exception} </blockquote>
                </div>
            `)
        } else {
            var link_url = json_parameters.link_url;
            if (link_url) {
                list_area.html(`
                <blockquote>
                    <h3>
                    <a href="${link_url}">Connect to ${module_name} / ${script_name} </a>
                    </h3>
                    (url=${link_url})
                </blockquote>`);
                if (json_parameters.redirect) {
                    redirect_to(link_url);
                }
            } else {
                var emodule = encodeURIComponent(module_name);
                var escript = encodeURIComponent(script_name);
                launch_url = `${url_prefix}?module=${emodule}&script=${escript}${link_arg}`;
                list_area.html(`
                <blockquote>
                    <h3>
                    <a href="${launch_url}">Launch ${module_name} / ${script_name} </a>
                    </h3>
                    (url=${launch_url})
                </blockquote>`);
                if (json_parameters.redirect) {
                    redirect_to(launch_url);
                }
            }
        }
    }
};