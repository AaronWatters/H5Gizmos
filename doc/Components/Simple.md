
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

## `RadioButtons`

## `CheckBoxes`

## `Image`

## `Plotter`

<a href="./README.md">
Return to Component categories.
</a>
