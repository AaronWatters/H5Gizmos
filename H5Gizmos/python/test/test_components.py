
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


def selenium_watcher_process(url, identity, snooze, retries, verbose=False):
    if verbose:
        print("watcher: getting driver")
    driver = webdriver.Chrome()
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
        fn = self.fullname()
        #startid = gz.new_identifier(fn + "-start")
        self.endid = gz.new_identifier(fn + "-end")
        #sentinel = gz.Html('<div id="%s">%s</div>' % (identity, identity))
        #main_component.add(sentinel)
        await self.main_component.link(
            await_start=False,
            shutdown_on_close=False,
            title = repr(fn) + " test"
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
        beatles = "John Paul George Ringo".split()
        favorites = "Paul Ringo".split()
        self.favorite_beatles = favorites
        cb = gz.CheckBoxes(beatles, favorites, legend="your favorite") #, on_click=self.checked)
        self.checkboxes = cb
        txt = self.txt = gz.Text("choose beatles")
        txt.css(color="green")
        children = [
            "Example Stack",
            [txt, cb],
            "End of stack"
        ]
        S = gz.Stack(children, css={"background-color": "cornsilk"})
        S.resize(width=600)
        return S
    
    async def logic(self):
        S = self.main_component
        width = await gz.get(S.element.width())
        self.assertEqual(width, 600)
        cb = self.checkboxes
        self.assertEqual(self.favorite_beatles, cb.selected_values)
        #print ("big sleep") ; time.sleep(100)
