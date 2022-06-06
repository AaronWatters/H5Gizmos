
// The URL prefix for links
var url_prefix = null;

function setup_start_page(json_parameters) {
    var location = window.location;
    url_prefix = location.origin + location.pathname;
    var textarea_info = "export GIZMO_LINK_PREFIX=" + url_prefix
    $('#gizmo_link_prefix').val(textarea_info);
}