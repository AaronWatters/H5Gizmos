# Adapted from https://takanori-fujiwara.github.io/d3-gallery-javascript/networks/chord-diagram/

from H5Gizmos import serve, Html, do

# Chart data as Python objects:
array2d = [
  [.096899, .008859, .000554, .004430, .025471, .024363, .005537, .025471],
  [.001107, .018272, .000000, .004983, .011074, .010520, .002215, .004983],
  [.000554, .002769, .002215, .002215, .003876, .008306, .000554, .003322],
  [.000554, .001107, .000554, .012182, .011628, .006645, .004983, .010520],
  [.002215, .004430, .000000, .002769, .104097, .012182, .004983, .028239],
  [.011628, .026024, .000000, .013843, .087486, .168328, .017165, .055925],
  [.000554, .004983, .000000, .003322, .004430, .008859, .017719, .004430],
  [.002215, .007198, .000000, .003322, .016611, .014950, .001107, .054264]
]
names = ['Apple', 'HTC', 'Huawei', 'LG', 'Nokia', 'Samsung', 'Sony', 'Other']
colors = ['#c4c4c4', '#69b40f', '#ec1d25', '#c8125c', '#008fc8', '#10218b', '#134b24', '#737373']

# Local web resources:
preamble = """
<link rel='stylesheet' type='text/css' href='./style/style.css'>
<script src='./script/d3.min.js'></script>
<script src='./script/load_chord_diagram.js' type='module'></script>
"""

async def task():
    header = Html("<div><h1>Chord Diagram</h1></div>")
    # Attach folders for web resources and load the resources:
    header.serve_folder("script", "./script")
    header.serve_folder("style", "./style")
    header.insert_html(preamble)
    # Start the interface.
    await header.show()
    # Construct the chart.
    window = header.window
    element = header.element
    do(window.append_chord_diagram(element, array2d, names, colors))

serve(task())
