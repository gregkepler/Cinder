import os
import globals as g
from globals import PATHS
import utils


class FileData(object):

    def __init__(self, tree, in_path):

        self.tree = tree  # xml file that describes the page
        self.bs4 = None  # html file of the actual page
        self.in_path = in_path

        self.name = ""
        self.title = ""
        self.page_header = ""
        self.search_tags = []
        self.path = ""
        self.kind = ""
        self.kind_explicit = ""
        self.out_path = ""
        self.is_searchable = True
        self.body_class = ""
        self.section = ""
        self.search_anchors = []

    def get_content(self):
        content = {
            "name": self.name,
            "title": self.title,
            "page_header": self.page_header,
        }
        return content


class ClassFileData(FileData):

    def __init__(self, tree, in_path):
        FileData.__init__(self, tree, in_path)
        self.description = None
        self.is_template = False
        self.template_def_name = ""
        self.includes = None
        self.typedefs = []
        self.classes = []
        self.related = []
        self.namespace_nav = None
        self.prefix = ""
        self.enumerations = []
        self.public_functions = []
        self.public_types = []
        self.public_static_functions = []
        self.anchors = []
        self.protected_functions = []
        self.protected_attrs = []
        self.class_hierarchy = None
        self.friends = []

        # fill compound name (with namespace if present)
        self.compoundName = str(utils.find_compound_name(tree))
        self.stripped_name = utils.strip_compound_name(self.compoundName)

        # stripped name (w/o namespace)
        name_parts = self.compoundName.rsplit("cinder::", 1)
        if len(name_parts) > 1:
            self.name = name_parts[1]  # without "cinder::"
        else:
            self.name = name_parts[0]

        # kind of file that we are parsing (class, namespace, etc)
        self.kind = utils.find_file_kind(tree)
        self.kind_explicit = utils.find_file_kind_explicit(tree)
        self.namespace = "::".join(self.compoundName.split("::")[0:-1])

        ns_list = self.compoundName.split("::")
        ns_links = []
        # make list of namespace links
        for index, ns in enumerate(ns_list[:-1]):
            ns_object = g.symbolsMap.find_namespace("::".join(ns_list[0:index + 1]))
            if ns_object:
                ns_link = utils.LinkData(utils.path_join(PATHS["HTML_DEST_PATH"], ns_object.path), ns)
            else:
                # add inactive link data
                ns_link = utils.LinkData("", ns, False)
            ns_links.append(ns_link)
        self.ns_links = ns_links

    def get_content(self):
        orig_content = super(ClassFileData, self).get_content()
        content = orig_content.copy()
        class_content = {
            "name": self.stripped_name,
            "namespace": self.namespace,
            "namespace_links": self.ns_links,
            "description": self.description,
            "is_template": self.is_template,
            "template_def_name": self.template_def_name,
            "side_nav_content": {
                "include": self.includes,
                "typedefs": {
                    "list": self.typedefs,
                    "length": len(self.typedefs)
                },
                "class_hierarchy": self.class_hierarchy,
                "classes": {
                    "list": self.classes,
                    "length": len(self.classes)
                },
                "related": {
                    "list": self.related,
                    "length": len(self.related)
                }
            },
            "namespace_nav": self.namespace_nav,
            "prefix": self.prefix,
            "enumerations": {
                "anchor": "enumerations",
                "list": self.enumerations,
                "length": len(self.enumerations)
            },
            "public_functions": {
                "anchor": "public-member-functions",
                "list": self.public_functions,
                "length": len(self.public_functions)
            },
            "public_static_functions": {
                "anchor": "public-static-functions",
                "list": self.public_static_functions,
                "length": len(self.public_static_functions)
            },
            "protected_functions": {
                "anchor": "protected-functions",
                "list": self.protected_functions,
                "length": len(self.protected_functions)
            },
            "protected_attrs": {
                "anchor": "protected-attrs",
                "list": self.protected_attrs,
                "length": len(self.protected_attrs)
            },
            "public_types": {
                "anchor": "public-types",
                "list": self.public_types,
                "length": len(self.public_types)
            },
            "friends": {
                "anchor": "friends",
                "list": self.friends,
                "length": len(self.friends)
            }
        }
        content.update(class_content)
        return content


class NamespaceFileData(FileData):

    def __init__(self, tree, in_path):
        FileData.__init__(self, tree, in_path)

        # stripped name (w/o namespace)
        self.compoundName = str(utils.find_compound_name(tree))
        self.name = self.compoundName

        self.namespaces = []
        self.classes = []
        self.typedefs = []
        self.enumerations = []
        self.functions = []
        self.free_functions = []
        self.variables = []
        self.namespace_nav = None
        self.kind = utils.find_file_kind(tree)
        self.kind_explicit = self.kind

    def get_content(self):
        orig_content = super(NamespaceFileData, self).get_content()
        content = orig_content.copy()
        ns_content = {
            "namespace_nav": self.namespace_nav,
            "namespaces": {
                "anchor": "namespaces",
                "list": self.namespaces,
                "length": len(self.namespaces)
            },
            "classes": {
                "anchor": "classes",
                "list": self.classes,
                "length": len(self.classes)
            },
            "typedefs": {
                "anchor": "typedefs",
                "list": self.typedefs,
                "length": len(self.typedefs)
            },
            "enumerations": {
                "anchor": "enumerations",
                "list": self.enumerations,
                "length": len(self.enumerations)
            },
            "public_functions": {
                "anchor": "functions",
                "list": self.functions,
                "length": len(self.functions)
            },
            "free_functions": {
                "anchor": "free_functions",
                "list": self.free_functions,
                "length": len(self.free_functions)
            },
            "variables": {
                "anchor": "variables",
                "list": self.variables,
                "length": len(self.variables)
            }
        }
        content.update(ns_content)
        return content


class GroupFileData(FileData):

    def __init__(self, tree, in_path, module_config):
        FileData.__init__(self, tree, in_path)
        self.description = ""
        self.prefix = ""
        self.typedefs = []
        self.name = str(utils.find_compound_name(tree))
        self.public_functions = []
        self.anchors = []
        self.config = module_config

        self.kind = "module"
        self.kind_explicit = self.kind

    def get_content(self):
        orig_content = super(GroupFileData, self).get_content()
        content = orig_content.copy()
        group_content = {
            "name": self.name,
            "description": self.description,
            "prefix": self.prefix,
            "typedefs": {
                "anchor": "typedefs",
                "list": self.typedefs,
                "length": len(self.typedefs)
            },
            "subgroups": {
                "anchor": "subgroups",
                "list": self.subgroups,
                "length": len(self.subgroups)
            },
            # "enumerations": {
            #     "anchor": "enumerations",
            #     "list": self.enumerations,
            #     "length": len(self.enumerations)
            # },
            "public_functions": {
                "anchor": "public-member-functions",
                "list": self.public_functions,
                "length": len(self.public_functions)
            }
            # "public_types": {
            #     "anchor": "public-types",
            #     "list": self.public_types,
            #     "length": len(self.public_types)
            # }
        }
        content.update(group_content)
        return content


class HtmlFileData(FileData):

    def __init__(self, in_path):
        FileData.__init__(self, None, in_path)

        self.html_content = ""
        self.group = None
        self.pagenav = []

        self.kind = "html"
        self.kind_explicit = self.kind

        if self.in_path.find("guides"+os.sep) > -1:
            self.kind_explicit = "guide"
        if self.in_path.find("reference"+os.sep) > -1:
            self.kind_explicit = "reference"

    def get_content(self):
        orig_content = super(HtmlFileData, self).get_content()
        content = dict(orig_content)
        template_content = {
            "html_content": self.html_content,
            "namespace_nav": str(g.namespace_nav),
            "pagenav": {
                "list": self.pagenav,
                "length": len(self.pagenav)
            }
        }
        content.update(template_content)
        return content