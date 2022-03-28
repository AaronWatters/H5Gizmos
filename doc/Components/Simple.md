
# Simple Gizmo Components

Simple components such as buttons and text do not contain other non-trivial components.

## `Text`

Initially

```Python
from H5Gizmos import Text

txt = Text("Old Text")
txt.css(color="green")
await txt.show()
```

<img src="Text0.png">

Changed

```Python
txt.css(color="red")
txt.text("New Text")
```

<img src="Text.png"/>

## `Button`

```Python
from H5Gizmos import Button

count = 0

def button_click_callback(*ignored):
    global count
    count += 1
    info.text("Clicked = " + str(count))
    
B = Button("Click me", on_click=button_click_callback)
await B.show()
info = B.add("No clicks yet")
```

<img src="Button.png"/>


## `ClickableText`

```Python
from H5Gizmos import ClickableText

count = 0

def text_click_callback(*ignored):
    global count
    count += 1
    CTinfo.text("Clicked = " + str(count))
    CTinfo.css(color="magenta")
    
CT = ClickableText("Click me", on_click=text_click_callback)
await CT.show()
CTinfo = CT.add("No clicks yet")
```

<img src="ClickableText.png">

## `Html`

```Python
from H5Gizmos import Html

H = Html("""
<table border>
    <tr>
        <th> Species </th> <th> Count </th>
    </tr>
    <tr>
        <td> Dog </td> <td> 5 </td>
    </tr>
    <tr>
        <td> Cat </td> <td> 0 </td>
    </tr>
</table>
""")
H.css({"background-color": "pink"})
await H.show()
```

<img src="Html0.png"/>

```Python
H.html("<h1>Have a nice day!</h1>")
```
<img src="Html1.png">

## `Input`

```Python
from H5Gizmos import Input

answer = Input(initial_value="-11")
await answer.show()
answer.add("What is six times seven?")
feedback = answer.add("Enter your answer in the box above, please.")
answer.focus()

def check(*ignored):
    entered = answer.value
    try:
        assert int(entered) == 6 * 7
    except Exception:
        feedback.text("Sorry: please try again.")
        answer.focus()
    else:
        feedback.text("Right!")
        
answer.on_enter(check)
```

<img src="Input.png"/>

## `LabelledInput`

```Python
from H5Gizmos import LabelledInput

LI = LabelledInput("What is your name? ")
await LI.label_container.show()

def on_response(*ignored):
    name = LI.value
    LI.label_container.add("Welcome " + repr(name))
    
LI.on_enter(on_response)
LI.focus()
```

<img src="LabelledInput.png">

## `Slider`

```Python
from H5Gizmos import Slider

def slide_callback(*ignored):
    v = S.value
    info.text("temperature = " + str(v))
    
S = Slider(
    minimum=-100,
    maximum=150.0,
    value=88.6,
    step=0.2,
    orientation="horizontal", # or "vertical"
    on_change=slide_callback,
)
S.resize(width=400)
await S.show()
info = S.add("temperature here...")
slide_callback()
```

<img src="Slider.png">

## `RangeSlider`

```Python
from H5Gizmos import RangeSlider

def r_slide_callback(*ignored):
    low = RS.low_value
    high = RS.high_value
    rinfo.text("from %s to %s." % (low, high))
    
RS = RangeSlider(
    minimum=-100,
    maximum=150.0,
    low_value=23.4,
    high_value=88.6,
    step=0.2,
    orientation="horizontal", # or "vertical"
    on_change=r_slide_callback,
)
RS.resize(width=400)
await RS.show()
rinfo = RS.add("temperature here...")
r_slide_callback()
```

<img src="RangeSlider.png"/>

## `DropDownSelect`

```Python
from H5Gizmos import DropDownSelect

pairs = [
    ("Bacterium", "Monera"),
    ("Single cell", "Protista"),
    ("Plant", "Plantae"),
    ("Animal", "Animalia"),
    ("Fungus", "Fungi"),
]

def dropdown_callback(*ignored):
    [kingdom_name] = D.selected_values
    kingdom.text("Kingdom is " + kingdom_name)

D = DropDownSelect(
    label_value_pairs = pairs,
    selected_value="Fungi",
    legend="What are you? ",
)
D.resize(height=200)

await D.show()
kingdom = D.add("Kingdom here.")
dropdown_callback()
```

<img src="DropDownSelect.png"/>


## `RadioButtons`

```Python
from H5Gizmos import RadioButtons

pairs = [
    ("Bacterium", "Monera"),
    ("Single cell", "Protista"),
    ("Plant", "Plantae"),
    ("Animal", "Animalia"),
    ("Fungus", "Fungi"),
]

def radio_callback(*ignored):
    [kingdom_name] = RD.selected_values
    rkingdom.text("Kingdom is " + kingdom_name)

RD = RadioButtons(
    label_value_pairs = pairs,
    selected_value="Fungi",
    legend="What are you? ",
    on_click=radio_callback,
)

await RD.show()
rkingdom = RD.add("Kingdom here.")
radio_callback()
```

<img src="RadioButtons.png"/>

## `CheckBoxes`

```Python
from H5Gizmos import CheckBoxes

pairs = [
    ("Bacterium", "Monera"),
    ("Single cell", "Protista"),
    ("Plant", "Plantae"),
    ("Animal", "Animalia"),
    ("Fungus", "Fungi"),
]

def check_callback(*ignored):
    names = CB.selected_values
    cbkingdom.text("Kingdoms: " + repr(names))

CB = CheckBoxes(
    label_value_pairs = pairs,
    selected_values=["Fungi", "Plantae"],
    legend="What are you? ",
    on_click=check_callback,
)

await CB.show()
cbkingdom = CB.add("Kingdom here.")
check_callback()
```

<img src="Checkboxes.png">

## `Image`

```Python
from H5Gizmos import Image

fn = "mandrill.png"
mandrill_bytes = open(fn, "rb").read()
Img = Image(fn, bytes_content=mandrill_bytes, height=100, width=100)
await Img.show()
```

<img src="Image1.png">

### Loading an array into a blank image

```Python
Blank = Image(height=100, width=200)
await Blank.show()
```

then later

```Python
import numpy as np
A = np.zeros((25,), dtype=np.ubyte) + 222
B = A.reshape((5,5))
B[4,:] = B[0,:] = B[:,4] = B[:,0] = 100
A[::2] = 0
Blank.change_array(B)
Blank.css({"image-rendering": "pixelated"})
```

<img src="Image2.png">

## `Plotter`

```Python
from H5Gizmos import Plotter
import matplotlib.pyplot as plt

plot_region = Plotter()

await plot_region.show()
```

then

```Python
import numpy as np
import matplotlib.pyplot as plt

theta = 6 * np.pi / 5
xs = [ np.sin(theta * i) for i in range(6) ]
ys = [ np.cos(theta * i) for i in range(6) ]

with plot_region:
    plt.plot(xs, ys)
    plt.title("Twinkle Twinkle Little Star")
```

<img src="Plotter.png">

<a href="./README.md">
Return to Component categories.
</a>
