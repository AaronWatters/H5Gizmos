
"""
End to end component tests.
"""

from selenium import webdriver
#from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
from multiprocessing import Process
import H5Gizmos as gz
import sys
import unittest
import asyncio
import numpy as np

# https://stackoverflow.com/questions/60296873/sessionnotcreatedexception-message-session-not-created-this-version-of-chrome
from webdriver_manager.chrome import ChromeDriverManager


def selenium_watcher_process(url, identity, snooze, retries, verbose=False):
    if verbose:
        print("watcher: getting driver")
    driver = webdriver.Chrome(ChromeDriverManager().install())
    if verbose:
        print("watcher: sleeping before url", url)
        time.sleep(60)
        print("watcher: getting url", repr(url))
    driver.get(url)
    #assert "Python" in driver.title
    #identity = "xxxx"
    elem = None
    if verbose:
        print("searching for identity", identity)
    for i in range(retries):
        time.sleep (snooze)
        try:
            elem = driver.find_element(By.ID, identity)
        except NoSuchElementException: 
            if verbose:
                print ("watcher", identity, "not found")
            pass
    if elem is not None:
        if verbose:
            print("watcher: element found!")
            #time.sleep(snooze * 10)
        pass
    else:
        if verbose:
            print("watcher: giving up...")
        pass
    driver.close()
    if verbose:
        print("watcher: close... sleeping")
        time.sleep(snooze * 10)

class ComponentCase(unittest.IsolatedAsyncioTestCase):

    snooze = 1
    retries = 10
    #html = "<h1>Initial test component</h1>"

    def fullname(o):
        # https://stackoverflow.com/questions/2020014/get-fully-qualified-class-name-of-an-object-in-python
        klass = o.__class__
        module_name = klass.__module__
        return module_name + '.' + klass.__qualname__
    
    def make_main_component(self):
        html = self.html
        return gz.Html(html)

    async def startup(self):
        self.main_component = self.make_main_component()
        started = await self.main_component.has_started()
        self.assertEqual(started, False)
        fn = self.fullname()
        #startid = gz.new_identifier(fn + "-start")
        self.endid = gz.new_identifier(fn + "-end")
        #sentinel = gz.Html('<div id="%s">%s</div>' % (identity, identity))
        #main_component.add(sentinel)
        await self.main_component.link(
            await_start=False,
            shutdown_on_close=False,
            title = repr(fn) + " test",
            verbose = True,
            )
        url = self.main_component.gizmo._entry_url()
        args = (url, self.endid, self.snooze, self.retries)
        print ("gizmo: starting watcher", args)
        self.watcher_process = Process(
            target=selenium_watcher_process,
            args=args)
        self.watcher_process.start()
        print("gizmo: awaiting component start")
        await self.main_component.has_started()
        url = self.main_component.entry_url()
        self.assertNotEqual(url, None)

    async def shutdown(self):
        print("signalling shutdown")
        identity = self.endid
        sentinel = gz.Html('<div id="%s">%s</div>' % (identity, identity))
        self.main_component.add(sentinel)
        # sleep to allow add to transmit
        await asyncio.sleep(self.snooze)
        print( "gizmo: waiting for watcher to exit")
        self.watcher_process.join(self.snooze * self.retries)
        #print( "gizmo: watcher, sleeping to free up connections...")
        #time.sleep(self.snooze)
        #sys.exit()

class BasicTest(ComponentCase):
    txt = "Initial header test component"
    html = "<h1>%s</h1>" % txt

    async def logic(self):
        txt = await gz.get(self.main_component.element.html())
        self.assertEqual(txt, self.txt)

    async def test_main(self):
        await self.startup()
        try:
            await self.logic()
        finally:
            await self.shutdown()

class CompositeTest(BasicTest):

    def make_main_component(self):
        # checkbox
        beatles = "John Paul George Ringo".split()
        favorites = "Paul Ringo".split()
        self.favorite_beatles = favorites
        cb = gz.CheckBoxes(beatles, favorites, legend="your favorite") #, on_click=self.checked)
        self.checkboxes = cb
        # simple text
        txt = self.txt = gz.Text("choose beatles")
        txt.css(color="green")
        # button
        B = self.button = gz.Button("Click me") #, on_click=button_click_callback)
        # clickable text
        CT = self.clickable_text = gz.ClickableText("I'm clickable", on_click=self.click_text)
        self.text_click_count = 0
        children = [
            "Example Stack",
            [txt, cb],
            [B, CT],
            "<b>End of stack</b>"
        ]
        S = gz.Stack(children, css={"background-color": "cornsilk"})
        S.resize(width=600)
        return S
    
    def click_text(self, *ignored):
        self.text_click_count += 1
        self.txt.text("Text clicked: " + repr(self.text_click_count))
        self.txt.css(color="magenta")
    
    async def logic(self):
        S = self.main_component
        # exercise on_shutdown
        def shutdown_callback(*ignored):
            print("shut down callback called.")
        S.on_shutdown(shutdown_callback)
        # test get using width
        width = await gz.get(S.element.width())
        self.assertEqual(width, 600)
        cb = self.checkboxes
        self.assertEqual(self.favorite_beatles, cb.selected_values)
        # exercise repr code...
        S.add("Text repr=" + repr(self.txt))
        # exercise error message
        S.error_message("Test error message... " + repr(cb.get_element()))
        # test javascript function creator
        func = S.function(["a", "b"], "return a+b")
        five = await gz.get(func(2,3))
        self.assertEqual(five, 5)
        # click text
        # https://stackoverflow.com/questions/7853302/jquery-programmatically-click-on-new-dom-element
        gz.do(self.clickable_text.element.trigger("click"))
        #print ("big sleep") ; time.sleep(100)
        # exercise store_json
        json_structure = {
            "none": None,
            "number": 3.1,
            "string": "Bohemian Rhapsody",
            "bool": False,
            "dictionary": {"lie": "falsehood"},
            "list": [1,2,"three"],
        }
        json_ref = await S.store_json(json_structure, "my_json")
        song = await gz.get(json_ref["string"])
        print("song=", song)
        self.assertEqual(song, "Bohemian Rhapsody")
        # exercise store_array
        A = (np.arange(1000) % 13 - 5).astype(np.int16)
        Aref = await S.store_array(A, "my_array")
        A6 = await gz.get(Aref[6])
        self.assertEqual(A6, A[6])
        B = await S.get_array_from_buffer(Aref, dtype=np.int16)
        ABdiff = np.abs(A - B).max()
        self.assertEqual(ABdiff, 0)
        S.uncache("my_array")

class TestSimpleMethods(unittest.TestCase):

    def test_shutdown_parent(self):
        import sys
        realexit = sys.exit
        def fake_exit(*args):
            print ("not really exitting", args)
        try:
            sys.exit = fake_exit
            component = gz.Html("<div>hello world</div>")
            component.shutdown_parent_only()
        finally:
            sys.exit = realexit

    def test_canvas_data(self):
        query = dict(height=1, width=1)
        bytes = b'1234'
        packet = (bytes, query)
        component = gz.Html("<div>hello world</div>")
        byte_array = component.array_from_canvas_data(packet)
        self.assertIsNotNone(bytearray)
