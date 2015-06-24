# -*- coding: utf-8 -*-
# Copyright (c) 2015, Vispy Development Team.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
"""
The classes in scene.visuals are visuals that may be added to a scenegraph
using the methods and properties defined in `vispy.scene.Node` such as name,
visible, parent, children, etc...

These classes are automatically generated by mixing `vispy.scene.Node` with
the Visual classes found in `vispy.visuals`.

For developing custom visuals, it is recommended to subclass from
`vispy.visuals.Visual` rather than `vispy.scene.Node`.
"""
import re
import weakref

from .. import visuals
from .node import Node
from ..visuals.filters import ColorFilter, PickingFilter


class VisualNode(Node):
    _next_id = 1
    _visual_ids = weakref.WeakValueDictionary()
    
    def __init__(self, parent=None, name=None):
        Node.__init__(self, parent=parent, name=name,
                      transforms=self.transforms)
        self._opacity_filter = ColorFilter()
        self.attach(self._opacity_filter)
        
        self._id = VisualNode._next_id
        VisualNode._visual_ids[self._id] = self
        VisualNode._next_id += 1
        self._picking_filter = PickingFilter(id=self._id)
        self.attach(self._picking_filter)

    def _update_opacity(self):
        self._opacity_filter.color = (1, 1, 1, self._opacity)
        
    def set_clipper(self, node, clipper):
        """Assign a clipper that is inherited from a parent node.
        
        If *clipper* is None, then remove any clippers for *node*.
        """
        if node in self._clippers:
            self.detach(self._clippers.pop(node))
        if clipper is not None:
            self.attach(clipper)
            self._clippers[node] = clipper

    @property
    def picking(self):
        """Boolean that determines whether this node (and its children) are
        drawn in picking mode.
        """
        return self._picking
    
    @picking.setter
    def picking(self, p):
        for c in self.children:
            c.picking = p
        if self._picking == p:
            return
        self._picking = p
        self._picking_filter.enabled = p
        self.update_gl_state(blend=not p)

    def _update_trsys(self, event):
        doc = self.document_node
        scene = self.scene_node
        root = self.root_node
        self.transforms.visual_transform = self.node_transform(scene)
        self.transforms.scene_transform = scene.node_transform(doc)
        self.transforms.document_transform = doc.node_transform(root)
        
        Node._update_trsys(self, event)

    
def create_visual_node(subclass):
    # Create a new subclass of Node.
    
    # Decide on new class name
    clsname = subclass.__name__
    assert clsname.endswith('Visual')
    clsname = clsname[:-6]
    
    # Generate new docstring based on visual docstring
    try:
        doc = generate_docstring(subclass, clsname)
    except Exception:
        # If parsing fails, just return the original Visual docstring
        doc = subclass.__doc__
    
    # New __init__ method
    def __init__(self, *args, **kwargs):
        parent = kwargs.pop('parent', None)
        name = kwargs.pop('name', None)
        self.name = name  # to allow __str__ before Node.__init__
        
        subclass.__init__(self, *args, **kwargs)
        VisualNode.__init__(self, parent=parent, name=name)
    
    # Create new class
    cls = type(clsname, (VisualNode, subclass), {'__init__': __init__, 
                                                 '__doc__': doc})
    
    return cls


def generate_docstring(subclass, clsname):
    # Generate a Visual+Node docstring by modifying the Visual's docstring
    # to include information about Node inheritance and extra init args.
    
    sc_doc = subclass.__doc__
    if sc_doc is None:
        sc_doc = ""
        
    # find locations within docstring to insert new parameters
    lines = sc_doc.split("\n")
    
    # discard blank lines at start
    while lines and lines[0].strip() == '':
        lines.pop(0)

    i = 0
    params_started = False
    param_indent = None
    first_blank = None
    param_end = None
    while i < len(lines):
        line = lines[i]
        # ignore blank lines and '------' lines
        if re.search(r'\w', line):  
            indent = len(line) - len(line.lstrip())
            # If Params section has already started, check for end of params
            # (that is where we will insert new params)
            if params_started:
                if indent < param_indent:
                    break
                elif indent == param_indent:
                    # might be end of parameters block..
                    if re.match(r'\s*[a-zA-Z0-9_]+\s*:\s*\S+', line) is None:
                        break
                param_end = i + 1
            
            # Check for beginning of params section
            elif re.match(r'\s*Parameters\s*', line):
                params_started = True
                param_indent = indent
                if first_blank is None:
                    first_blank = i
        
        # Check for first blank line
        # (this is where the Node inheritance description will be 
        # inserted)
        elif first_blank is None and line.strip() == '':
            first_blank = i

        i += 1
        if i == len(lines) and param_end is None:
            # reached end of docstring; insert here
            param_end = i

    # If original docstring has no params heading, we need to generate it.
    if not params_started:
        lines.extend(["", "    Parameters", "    ----------"])
        param_end = len(lines)
        if first_blank is None:
            first_blank = param_end - 3
        params_started = True
    
    # build class and parameter description strings
    class_desc = ("\n    This class inherits from visuals.%sVisual and "
                  "scene.Node, allowing the visual to be placed inside a "
                  "scenegraph.\n" % (clsname))
    parm_doc = ("    parent : Node\n"
                "        The parent node to assign to this node (optional).\n"
                "    name : string\n"
                "        A name for this node, used primarily for debugging\n"
                "        (optional).")
    
    # assemble all docstring parts
    lines = (lines[:first_blank] +
             [class_desc] +
             lines[first_blank:param_end] +
             [parm_doc] +
             lines[param_end:])
            
    doc = '\n'.join(lines)
    return doc


__all__ = []

for obj_name in dir(visuals):
    obj = getattr(visuals, obj_name)
    if (isinstance(obj, type) and 
       issubclass(obj, visuals.BaseVisual) and 
       obj is not visuals.Visual):
        cls = create_visual_node(obj)
        globals()[cls.__name__] = cls
        __all__.append(cls.__name__)
