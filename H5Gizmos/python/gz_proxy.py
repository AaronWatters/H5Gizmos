"""
Generic proxy support for H5Gizmos.
"""

import H5Gizmos as gz

def the_reference(reference):
    "Get the JavaScript reference that the given value represents, if it's a proxy, otherwise return the value itself."
    if isinstance(reference, Proxy):
        return reference.js_reference
    else:
        return reference
    
def the_arguments(args):
    "Get the JavaScript references that the given list of arguments represents, if any of them are proxies, otherwise return the arguments themselves."
    return [the_reference(arg) for arg in args]

class JSDescriptor:

    """
    A python descriptor that refers to a Javascript attribute.
    Setting the attribute will set the Javascript attribute, 
    and getting the attribute will get a *proxy* that can be used to get or set the Javascript attribute.
    """

    def __init__(self, constructor=None):
        self.constructor = constructor

    def __set_name__(self, owner, name):
        self.name = name
        #self.from_component = owner.from_component

    def __get__(self, instance, owner):
        """Return a proxy for the JavaScript attribute."""
        constructor = self.constructor or Proxy
        source_js_reference = instance.js_reference
        js_reference = source_js_reference[self.name]
        return constructor(js_reference, from_component=instance.from_component)
    
    def __set__(self, instance, value):
        """Set the JavaScript attribute to the given value."""
        final_value = the_reference(value)
        js_reference = instance.js_reference
        gz.do(js_reference._set(self.name, final_value))

class Proxy:

    def __init__(self, js_reference, from_component):
        self.js_reference = js_reference
        self.from_component = from_component

    async def _get_value(self):
        "Get the value of the JavaScript reference that this proxy represents (for suitable JavaScript references)."
        return await gz.get(self.js_reference)
    
    def _cache_result_proxy(self, method_name, constructor=None, args=[]):
        "Call the given method on the JavaScript reference that this proxy represents, and return a proxy for the result."
        args = the_arguments(args)
        result_js_reference = self.js_reference[method_name](*args)
        cache_reference = self.from_component.cache(None, result_js_reference, soft=True)
        constructor = constructor or Proxy
        return constructor(cache_reference, from_component=self.from_component)
    
    def _cache_new_result_proxy(self, method_name, constructor=None, args=[]):
        """
        Call the given method as a constructor on the JavaScript reference that this proxy represents, 
        and return a proxy for the result.  Useful for

        G = new THREE.SPhereGeometry( 70, 32, 16 );

        for example.
        """
        args = the_arguments(args)
        component = self.from_component
        result_js_reference = component.new(self.js_reference[method_name], *args)
        cache_reference = self.from_component.cache(None, result_js_reference, soft=True)
        constructor = constructor or Proxy
        return constructor(cache_reference, from_component=self.from_component)
    
    def _immediate_call(self, method_name, args=[]):
        "Call the given method on the JavaScript reference that this proxy represents immediately, without caching the result, and return the result."
        args = the_arguments(args)
        call_ref = self.js_reference[method_name](*args)
        gz.do(call_ref)
        return self # for possible chaining.


# Example usage:

class MiniDOMElementProxy(Proxy):

    innerHTML = JSDescriptor()

    textContent = JSDescriptor()

    def appendChild(self, reference):
        # if the reference is a proxy, get the JavaScript reference that it represents
        #child_js_reference = the_reference(reference)
        #gz.do(self.js_reference.appendChild(child_js_reference))
        return self._immediate_call("appendChild", args=[reference])


class miniURLProxy(Proxy):

    href = JSDescriptor()
    host = JSDescriptor()
    path = JSDescriptor()

class MiniDocumentProxy(Proxy):

    location = JSDescriptor()

    title = JSDescriptor()

    body = JSDescriptor(MiniDOMElementProxy)

    def createElement(self, tag_name):
        return self._cache_result_proxy("createElement", constructor=MiniDOMElementProxy, args=[tag_name])


def get_window_proxy(component):
    "Get a proxy for the window of the given component."
    return MiniWindowProxy(component.window, from_component=component)

class MiniWindowProxy(Proxy):

    def alert(self, message):
        gz.do(self.js_reference.alert(message))

    document = JSDescriptor(MiniDocumentProxy)

    def URL(self, url_string):
        return self._cache_new_result_proxy("URL", constructor=miniURLProxy, args=[url_string])

    