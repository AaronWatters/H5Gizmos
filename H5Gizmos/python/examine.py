
import numpy as np
import H5Gizmos as gz
import collections
import html

SHORT_LENGTH = 50  # Abbreviate strings to this size.
PAGING = 20    # break sequences into this size.

async def examine(object, link=True):
    """
    Create and display an interactive explorer for an object.
    """
    exp = explorer(object)
    gizmo = exp.gizmo()
    if link:
        await gizmo.link()
    else:
        await gizmo.show()

def explorer(object):
    """
    Create an interactive explorer for an object.
    """
    ty = type(object)
    if ty in (int, bool, float, complex) or np.isscalar(object):
        return ScalarExplorer(object)
    if ty is str:
        return StringExplorer(object)
    if ty is np.ndarray:
        return NdArrayExplorer(object)
    if isinstance(object, collections.abc.Sequence):
        return SequenceExplorer(object)
    if isinstance(object, collections.abc.Mapping):
        return MappingExplorer(object)
    try:
        return VarsExplorer(object)
    except TypeError:
        pass
    # default
    return UnknownDisplay(object)

class Explorer:

    "Superclass for common explorer methods"

    def typename(self):
        return type(self.object).__name__

    def short_description(self):
        R = repr(self.object)
        if len(R) > SHORT_LENGTH:
            R = R[:SHORT_LENGTH] + "..."
        return html.escape("%s :: %s" % (R, self.typename()))

    def short_html(self):
        return gz.Html("<span> %s </span>" % self.short_description())

class ScalarExplorer(Explorer):

    "Display a simple number-like object."

    def __init__(self, object):
        self.object = object

    def gizmo(self):
        return gz.Text(self.short_description())

class UnknownDisplay(ScalarExplorer):
    
    def gizmo(self):
        return gz.Text("??" + self.short_description())

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
            return gz.Text(self.short_description())
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
        short = self.short_description()
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

    def short_description(self):
        ob = self.object
        ln = len(ob)
        if ln < SHORT_LENGTH:
            return repr(ob)
        trunc = ob[:SHORT_LENGTH]
        return "%s... [%s]" % (repr(trunc), ln)

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

    def short_description(self):
        t = self.typename()
        l = len(self.object)
        return "%s of length %s" % (t, l)

    def expanded_list(self):
        limit = self.limit
        viewed = list(self.object)[:limit]
        gizmos = [explorer(x).gizmo() for x in viewed]
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

    def short_description(self):
        ob = self.object
        shape = ob.shape
        dtype = ob.dtype
        return "ndarray of %s %s" % (dtype, shape)

class MappingExplorer(SequenceExplorer):

    key_sequence = None

    def expanded_list(self):
        ob = self.object
        if self.key_sequence is None:
            self.key_sequence = list(ob.keys())
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
        return gz.Stack([desc, ["vars", vars_gizmo]])
