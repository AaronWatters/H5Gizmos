from H5Gizmos import Html, CheckBoxes, serve

event_count = 0
greeting = Html("<div> EVENT AREA </div>")
greeting.resize(width=400, height=200)
greeting.css({"background-color": "yellow", "color": "green"})

events = "mousedown mousemove mouseout mouseover mouseup".split()

def select_callback(*ignored):
    checked_events = event_selection.selected_values
    for event in events:
        info.text("Checked: " + repr(checked_events))
        greeting.off(event)
        if event in checked_events:
            greeting.on(event, callback=event_callback)

def event_callback(event_info):
    global event_count
    event_count += 1
    event_name = event_info["type"]
    info.text("Event fired: " + repr((event_name, event_count)))

event_selection = CheckBoxes(events, legend="Check to enable events", on_click=select_callback)
info = Html("<p>No events</p>")

async def task():
    await greeting.show()
    greeting.add(event_selection)
    greeting.add(info)
    
serve(task())
