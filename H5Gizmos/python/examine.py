
"""
Gizmos for interactively exploring Python structures.
"""

import numpy as np
import H5Gizmos as gz
import collections
import html
import sys
import types
import traceback

SHORT_LENGTH = 50  # Abbreviate strings to this size.
PAGING = 20    # break sequences into this size.

async def examine(object, link=True, expand=False):
    """
    Create and display an interactive explorer for an object.
    """
    exp = explorer(object)
    exp.expanded = expand
    #print("exp is", exp)
    gizmo = exp.gizmo()
    if link:
        await gizmo.link()
    else:
        await gizmo.show()

def explorer(object):
    """
    Create an interactive explorer for an object.
    """
    if object is None:
        return NoneExplorer(object)
    ty = type(object)
    if (ty is not str) and (ty in (int, bool, float, complex) or (np.isscalar(object))):
        return ScalarExplorer(object)
    if ty is str:
        return StringExplorer(object)
    if ty is np.ndarray:
        if not object.shape:
            return ScalarExplorer(object)
        return NdArrayExplorer(object)
    if isinstance(object, collections.abc.Sequence):
        return SequenceExplorer(object)
    if isinstance(object, collections.abc.Mapping):
        return MappingExplorer(object)
    if ty is types.TracebackType:
        return TracebackExplorer(object)
    if ty is traceback.FrameSummary:
        return FrameSummaryExplorer(object)
    try:
        return VarsExplorer(object)
    except TypeError:
        pass
    if hasattr(object, "__slots__"):
        return SlottedObjectExplorer(object)
    # default
    return UnknownDisplay(object)

class Explorer:

    "Superclass for common explorer methods"

    def typename(self):
        return type(self.object).__name__

    def short_description(self, escape=True):
        R = repr(self.object)
        if len(R) > SHORT_LENGTH:
            R = R[:SHORT_LENGTH] + "..."
        result = "%s :: %s" % (R, self.typename())
        if escape:
            result = html.escape("%s :: %s" % (R, self.typename()))
        #print("short html", repr(result))
        #raise ValueError(result)
        return result

    def short_html(self):
        #print(self.short_description)
        return gz.Html("<span> %s </span>" % self.short_description(escape=True))

class ScalarExplorer(Explorer):

    "Display a simple number-like object."

    def __init__(self, object):
        self.object = object

    def gizmo(self):
        return gz.Text(self.short_description(escape=False))

class NoneExplorer(ScalarExplorer):

    def gizmo(self):
        return gz.Text("None")


class UnknownDisplay(ScalarExplorer):
    
    def gizmo(self):
        return gz.Text("??" + self.short_description(escape=False))

class ExpandableExplorer(Explorer):

    "Superclass for expandables."

    expandable = True
    expanded = False
    gizmo = None

    def expand(self, *ignored):
        self.expanded = True
        self.reset_gizmo()

    def collapse(self, *ignored):
        self.expanded = False
        self.reset_gizmo()

    def gizmo(self):
        if not self.expandable:  # eg; for short strings
            return self.short_html()
        prefix = self.prefix()
        detail = self.detail()
        self._gizmo = gz.Shelf([prefix, detail])
        return self._gizmo

    def reset_gizmo(self):
        prefix = self.prefix()
        detail = self.detail()
        self._gizmo.attach_children([prefix, detail])

    def prefix(self):
        if self.expanded:
            return gz.ClickableText(" V ", on_click=self.collapse)
        else:
            return gz.ClickableText(" &gt; ", on_click=self.expand)

    def detail(self):
        short = self.short_description(escape=False)
        if self.expanded:
            more = self.expanded_list()
            first = gz.ClickableText(short, on_click=self.collapse)
            return gz.Stack([first] + more)
        else:
            return gz.ClickableText(short, on_click=self.expand)

class StringExplorer(ExpandableExplorer):

    def __init__(self, object):
        assert type(object) is str
        self.object = object
        # only expand longer strings
        self.expandable = (len(object) > SHORT_LENGTH)

    def short_description(self, escape=True):
        ob = self.object
        ln = len(ob)
        if ln < SHORT_LENGTH:
            result = repr(ob)
        else:
            trunc = ob[:SHORT_LENGTH]
            result = "%s... [%s]" % (repr(trunc), ln)
        if escape:
            return html.escape(result)
        return result

    def expanded_list(self):
        q = html.escape(self.object)
        pre = "<pre> %s </pre>" % q
        return [gz.Html(pre)]

class SequenceExplorer(ExpandableExplorer):

    def __init__(self, object):
        self.object = object
        self.expandable = (len(object) > 0)
        self.limit = PAGING
        # xxxx eventually add expandable limits...

    def lengthen(self, *ignored):
        assert self.limit < len(self.object)
        self.limit += PAGING
        self.reset_gizmo()

    def shorten(self, *ignored):
        assert self.limit > PAGING
        self.limit -= PAGING
        self.reset_gizmo()

    def short_description(self, escape=True):
        t = self.typename()
        l = len(self.object)
        return "%s of length %s" % (t, l)

    def expanded_list(self):
        limit = self.limit
        viewed = list(self.object)[:limit]
        gizmos = [[repr(i) + ":", explorer(x).gizmo()] for (i, x) in enumerate(viewed)]
        gizmos = self.add_paging(gizmos)
        return gizmos

    def add_paging(self, gizmos):
        limit = self.limit
        l = len(self.object)
        if limit > PAGING:
            gizmos.append(gz.ClickableText(" &lt;&lt;less ", on_click=self.shorten))
        if limit < l:
            gizmos.append(gz.ClickableText(" more&gt;&gt; ", on_click=self.lengthen))
        return gizmos

class NdArrayExplorer(SequenceExplorer):

    def short_description(self, escape=True):
        ob = self.object
        shape = ob.shape
        dtype = ob.dtype
        return "ndarray of %s %s" % (dtype, shape)

class MappingExplorer(SequenceExplorer):

    key_sequence = None

    def expanded_list(self):
        ob = self.object
        if self.key_sequence is None:
            self.key_sequence = list(sorted(ob.keys()))
        limit = self.limit
        viewed_keys = self.key_sequence[:limit]
        gizmos = []
        for k in viewed_keys:
            v = ob[k]
            k_gizmo = explorer(k).gizmo()
            v_gizmo = explorer(v).gizmo()
            stack = gz.Stack([k_gizmo, [" -> ", v_gizmo]])
            gizmos.append(stack)
        gizmos = self.add_paging(gizmos)
        return gizmos

class VarsExplorer(Explorer):

    def __init__(self, object):
        self.object = object
        self.vars = vars(object)  # may raise TypeError

    def gizmo(self):
        desc = self.short_html()
        vars_gizmo = explorer(self.vars).gizmo()
        #return gz.Stack([desc, "vars", vars_gizmo])
        return gz.Stack([desc, vars_gizmo])

class TracebackExplorer(Explorer):

    def __init__(self, object):
        self.object = object

    def gizmo(self):
        ob = self.object
        desc = self.short_html()
        extracted = traceback.extract_tb(ob)
        try:
            stack = traceback.extract_stack(ob)
        except Exception as e:
            stack = "Stack exception: " + repr(e)
        D = dict(extracted=extracted, stack=stack)
        D_gizmo = explorer(D).gizmo()
        #return gz.Stack([desc, "vars", vars_gizmo])
        return gz.Stack([desc, D_gizmo])

class FrameSummaryExplorer(Explorer):

    def __init__(self, object):
        self.object = object

    def gizmo(self):
        ob = self.object
        desc = self.short_html()
        D = dict(filename=ob.filename, lineno=ob.lineno, name=ob.name, locals=ob.locals)
        D_gizmo = explorer(D).gizmo()
        #return gz.Stack([desc, "vars", vars_gizmo])
        return gz.Stack([desc, D_gizmo])

class SlottedObjectExplorer(Explorer):

    def __init__(self, object):
        self.object = object

    def gizmo(self):
        ob = self.object
        desc = self.short_html()
        D = {name: getattr(ob, name) for name in ob.__slots__}
        D_gizmo = explorer(D).gizmo()
        #return gz.Stack([desc, "vars", vars_gizmo])
        return gz.Stack([desc, D_gizmo])

def execute_environment(code):
    import traceback
    exc = tb = None
    try:
        exec(code)
    except Exception as e:
        exc = e
        (ty, val, tb) = sys.exc_info()
    return dict(
        code=code,
        locals=locals(),
        globals=globals(),
        exception=exc,
        traceback=tb,
    )

async def execution_task(code):
    env = execute_environment(code)
    await examine(env, link=True, expand=True)

def examine_environment(code):
    gz.serve(execution_task(code))
