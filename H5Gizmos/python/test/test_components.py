
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


def selenium_watcher_process(url, identity, snooze, retries):
    #print("watcher: getting driver")
    driver = webdriver.Chrome()
    #print("watcher: getting url", repr(url))
    driver.get(url)
    #assert "Python" in driver.title
    #identity = "xxxx"
    elem = None
    #print("searching for identity", identity)
    for i in range(retries):
        time.sleep (snooze)
        try:
            elem = driver.find_element(By.ID, identity)
        except NoSuchElementException: 
            #print ("watcher", identity, "not found")
            pass
    if elem is not None:
        #print("watcher: element found!  sleeping")
        #time.sleep(snooze)
        pass
    else:
        #print("watcher: giving up...")
        pass
    driver.close()
    #print("watcher: close...")

class ComponentCase(unittest.IsolatedAsyncioTestCase):

    snooze = 1
    retries = 10
    html = "<h1>Initial test component</h1>"

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
        print( "gizmo: waiting for watcher to exit")
        self.watcher_process.join(self.snooze * self.retries)
        print( "gizmo: watcher exitted")
        #sys.exit()

class HeaderTest(ComponentCase):
    txt = "Initial header test component"
    html = "<h1>%s</h1>" % txt

    async def test_header(self):
        await self.startup()
        try:
            txt = await gz.get(self.main_component.element.html())
            self.assertEqual(txt, self.txt)
        finally:
            await self.shutdown()
