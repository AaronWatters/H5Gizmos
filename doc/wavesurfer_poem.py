
from H5Gizmos import Html, Text, Button, Stack, serve, do

# Here is a remote audio data file we want to load
poem_path = "./song_cjrg_teasdale_64kb.mp3"
poem_url = "poem.mp3"
wavesurfer_js = "https://unpkg.com/wavesurfer.js"

wave = Html("<div>Wavesurfer not yet attached.</div>")
wave.remote_js(wavesurfer_js)
wave.add_content(poem_path, "audio/mpeg", poem_url)

Attach_button = Button("Attach")
Play_button = Button("Play")
Pause_button = Button("Pause")

info = Text("This is the info area for the dashboard.")

def on_ready(*ignored):
    Play_button.set_on_click(play)
    Pause_button.set_on_click(pause)
    info.text("Audio is loaded and ready.")

def attach(*ignored):
    wave.js_init("""
        // THIS IS INJECTED JAVASCRIPT CODE
        
        // Clear the JQuery element associated with the gizmo component:
        element.empty();

        // Create and store the WaveSurfer visualization
        element.wavesurfer = WaveSurfer.create({
            // Attach the visualization to the DOM element for the component,
            container: element[0]
        });

        // Load the audio file.
        element.wavesurfer.load(url);

        // when the audio file is loaded, enable the control buttons
        element.wavesurfer.on('ready', function () {
            on_ready();
        });
    """, url=poem_url, on_ready=on_ready)
    info.text("Attached: audio.")

Attach_button.set_on_click(attach)

def pause(*ignored):
    do(wave.element.wavesurfer.pause())
    info.text("Paused.")

def play(*ignored):
    do(wave.element.wavesurfer.play())
    info.text("Playing.")

Dashboard = Stack([
    wave,
    [Attach_button, Play_button, Pause_button],
    info
])

async def task():
    await Dashboard.show()

serve(task())