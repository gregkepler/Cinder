import globals
from globals import PATHS
from utils import log, strip_compound_name, parse_arg_list, parse_xml
from bs4utils import *
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re

def generate_symbol_map():
    """
    Returns a dictionary from Cinder class name to file path
    """
    log("generating symbol map from tag file", 0, True)
    symbol_map = SymbolMap(globals.config)


    # find classes
    g_tag_xml = ET.ElementTree(ET.parse(globals.PATHS["TAG_FILE_PATH"]).getroot())
    class_tags = g_tag_xml.findall(r'compound/[@kind="class"]')
    for c in class_tags:
        class_obj = SymbolMap.Class(c)
        name = class_obj.qualifiedName

        # skip over blacklisted classes that belong to a blacklisted namespace
        if any(name.find(blacklisted) > -1 for blacklisted in globals.config.CLASS_LIST_BLACKLIST):
            # print "SKIPPING " + name
            continue

        base_class = class_obj.base
        symbol_map.classes[name] = class_obj

        # find functions and add to symbol map
        members = c.findall(r"member[@kind='function']")
        for member in members:

            # function_obj = SymbolMap.Function(fn_name, base_class, args, file_path)
            function_obj = SymbolMap.Function(member, base_class)

            # symbol_map.functions[name + "::" + function_obj.name] = function_obj
            symbol_map.add_function(name, function_obj.name, function_obj)
            class_obj.add_function(function_obj.name, function_obj)

        # print "CLASS: " + name
        # if name == "Iter":
        #     raise

        # find enums
        for member in c.findall(r"member/[@kind='enumeration']"):
            pre = name + "::" if name is not None else ""
            enum_name = pre + member.find("name").text
            anchor = member.find("anchor").text
            path = member.find("anchorfile").text + "#" + anchor
            enum_obj = SymbolMap.Enum(enum_name, path)
            symbol_map.enums[enum_name] = enum_obj

    # find structs
    struct_tags = g_tag_xml.findall(r'compound/[@kind="struct"]')
    for s in struct_tags:
        struct_obj = SymbolMap.Class(s)
        name = struct_obj.qualifiedName
        base_class = struct_obj.base

        # skip over blacklisted classes that belong to a blacklisted namespace
        if any(name.find(blacklisted) > -1 for blacklisted in globals.config.CLASS_LIST_BLACKLIST):
            log("SKIPPING " + name, 1)
            continue

        symbol_map.classes[name] = struct_obj

        # find functions and add to symbol map
        members = s.findall(r"member[@kind='function']")
        for member in members:
            # fn_name = member.find("name").text
            # anchor = member.find("anchor").text
            # file_path = member.find("anchorfile").text + "#" + anchor
            # args = member.find("argsstring").text if member.find("argsstring") else ""
            # function_obj = SymbolMap.Function(fn_name, base_class, args, file_path)
            function_obj = SymbolMap.Function(member, base_class)
            # symbol_map.functions[name + "::" + function_obj.name] = function_obj
            symbol_map.add_function(name, function_obj.name, function_obj)
            struct_obj.add_function(function_obj.name, function_obj)

    # find namespaces
    ns_tags = g_tag_xml.findall(r'compound/[@kind="namespace"]')

    for ns in ns_tags:
        namespace_name = ns.find('name').text
        file_name = ns.find('filename').text

        # skip namespaces with '@' in them
        if namespace_name.find('@') > -1:
            continue

        # skip over blacklisted classes that belong to a blacklisted namespace
        if globals.config.is_namespace_blacklisted(namespace_name):
            log("SKIPPING NAMESPACE: " + namespace_name, 1)
            continue

        ns_obj = SymbolMap.Namespace(namespace_name, file_name)
        symbol_map.namespaces[namespace_name] = ns_obj

        # process all typedefs in namespace
        typedef_list = add_typedefs(ns.findall(r"member/[@kind='typedef']"), namespace_name, symbol_map)
        ns_obj.typedefs = typedef_list

        # find enums
        for member in ns.findall(r"member/[@kind='enumeration']"):
            name = namespace_name + "::" + member.find("name").text
            # print "ENUM: " + name
            anchor = member.find("anchor").text
            path = member.find("anchorfile").text + "#" + anchor
            enum_obj = SymbolMap.Enum(name, path)
            symbol_map.enums[name] = enum_obj

        # find functions and add to symbol map
        members = ns.findall(r"member[@kind='function']")
        for member in members:
            function_obj = SymbolMap.Function(member, base_class)
            ns_obj.functionList.append(function_obj)
            ns_obj.add_function(function_obj.name, function_obj)

    # find files
    file_tags = g_tag_xml.findall(r'compound/[@kind="file"]')
    for f in file_tags:
        name = f.find('name').text
        # filePath = f.find('path').text + f.find('filename').text
        file_path = f.find('path').text + name
        typedefs = []

        # find typedefs for each file
        for t in f.findall(r'member[@kind="typedef"]'):
            td_name = t.find("name").text
            type_name = t.find("type").text
            type_path = t.find('anchorfile').text + "#" + t.find("anchor").text
            typedef = SymbolMap.Typedef(td_name, type_name, type_path)
            typedefs.append(typedef)

        # print "FILE PATH: " + name + " | " + file_path
        symbol_map.files[name] = SymbolMap.File(name, file_path, typedefs)

        # find functions for each file
        for member in f.findall(r'member[@kind="function"]'):
            function_obj = SymbolMap.Function(member, "")
            symbol_map.add_function("", function_obj.name, function_obj)

    # find groups
    group_tags = g_tag_xml.findall(r'compound/[@kind="group"]')
    for member in group_tags:
        group_obj = SymbolMap.Group(member)
        subgroups = member.findall('subgroup')

        # hardcode this for now since all groups are part of glm
        ns = "glm"

        # add subgroup names
        if len(subgroups) > 0:
            for subgroup in subgroups:
                group_obj.subgroup_names.append(subgroup.text)

        # find functions and add to symbol map
        functions = member.findall(r"member[@kind='function']")
        for function in functions:
            function_obj = SymbolMap.Function(function, ns)
            group_obj.add_function(function_obj.name, function_obj)
            symbol_map.add_function(ns, function_obj.name, function_obj)

        # find typedefs
        typedefs = member.findall(r"member/[@kind='typedef']")
        add_typedefs(typedefs, "glm", symbol_map)

        symbol_map.groups[group_obj.name] = group_obj

    # link up subgroups to parent groups
    for group_names in symbol_map.groups:
        group_obj = symbol_map.find_group(group_names)
        if len(group_obj.subgroup_names) > 0:
            # print group.name
            for subgroup_name in group_obj.subgroup_names:
                subgroup = symbol_map.find_group(subgroup_name)
                group_obj.subgroups.append(subgroup)

    if len(file_tags) == 0:
        log("no compound of type 'file' found in tag file. Check doxygen SHOW_FILES setting.", 1)

    return symbol_map


def add_typedefs(typedefs, ns_name, symbol_map):
    typedef_list = []
    # if ns_name == "cinder::gl"
    for typdef in typedefs:
        name = typdef.find("name").text
        type_name = typdef.find("type").text
        full_name = ns_name + "::" + name
        shared_from_class = None

        if type_name.startswith("class") > 0:
            shared_from_class = symbol_map.find_class(type_name.split("class ")[1])

        elif type_name.find("shared") > 0:
            if type_name.find("class"):
                shareds = re.findall(r"std::shared_ptr< (?:class)* *([\w]*) >", type_name)
            else:
                shareds = re.findall(r"std::shared_ptr< *([\w]*) >", type_name)

            if len(shareds) > 0:
                base = ns_name + "::" + shareds[0]
                shared_from_class = symbol_map.find_class(base)

        if not shared_from_class:
            # find based on the string in type that's not explicitly a shared_ptr
            # such as <type>SurfaceT&lt; uint8_t &gt;</type>
            shareds = re.findall(r"([A-Za-z0-9]*)", type_name)
            shared_from_class = symbol_map.find_class(shareds[0])

        file_path = typdef.find('anchorfile').text + "#" + typdef.find("anchor").text
        type_def_obj = SymbolMap.Typedef(name, type_name, file_path)

        if shared_from_class is not None and type(shared_from_class) == SymbolMap.Class:
        # if shared_from_class is not None:
            type_def_obj.sharedFrom = shared_from_class
            # let the class know that it has some typedefs associated with it
            shared_from_class.add_type_def(type_def_obj)

        symbol_map.typedefs[full_name] = type_def_obj
        typedef_list.append(type_def_obj)
    return typedef_list


# mapping for the tag file with helper functions
class SymbolMap(object):
    def __init__(self, config):
        self.namespaces = {}
        self.classes = {}
        self.typedefs = {}
        self.functions = {}
        self.files = {}
        self.enums = {}
        self.groups = {}
        self.config = config;

    class Class(object):
        def __init__(self, class_tree):

            # name with namespace
            self.qualifiedName = class_tree.find('name').text
            # name without namespace
            self.name = strip_compound_name(self.qualifiedName)
            self.path = class_tree.find('filename').text
            self.base = class_tree.find('base').text if class_tree.find('base') is not None else ""
            self.is_template = True if class_tree.find('templarg') is not None else False

            self.functionList = []
            self.relatedLinks = []
            self.type_defs = []

            # Path the the description prefix
            self.prefix_content = None

            # list of tags to be added to the search index
            self.tags = []
            self.tags.append(self.name)

        def add_related_link(self, link_data):
            # check for dupes
            if not any(link.link == link_data.link for link in self.relatedLinks):
                self.relatedLinks.append(link_data)

        def define_prefix(self, content):
            self.prefix_content = content

        def add_type_def(self, type_def_obj):
            self.type_defs.append(type_def_obj)
            # add typedef string to search tags
            self.tags.append(strip_compound_name(type_def_obj.name))

        def add_function(self, fn_name, fn_obj):
            self.functionList.append(fn_obj)

            # add as a tag if not a duplicated name
            if not any(tag == fn_name for tag in self.tags):
                self.tags.append(fn_name)

    class Namespace(object):
        def __init__(self, name, file_name):
            self.name = name
            self.path = file_name
            self.functionList = []
            self.tags = []
            self.tags.append(self.name)
            self.typedefs = []

            # add all namespace parts to search tags
            for part in self.name.split("::"):
                self.tags.append(part)

        def add_function(self, fn_name, fn_obj):
            self.functionList.append(fn_obj)

            # add as a tag if not a duplicate name
            if not any(tag == fn_name for tag in self.tags):
                self.tags.append(fn_name)

    class Typedef(object):
        def __init__(self, name, type_def, path):
            self.name = name
            self.type = type_def
            self.path = path
            self.sharedFrom = None

    class Function(object):
        def __init__(self, member_tree, base_class=None):
            anchor = member_tree.find("anchor").text
            self.name = member_tree.find("name").text
            self.base = base_class
            self.path = member_tree.find("anchorfile").text + "#" + anchor
            self.args = parse_arg_list(member_tree.find("arglist").text)

    class File(object):
        def __init__(self, name, path, typedefs):
            self.name = name
            self.path = path
            self.typedefs = typedefs
            rel_path_arr = self.path.split(globals.PATHS["PARENT_DIR"].replace("\\", "/"))
            self.relPath = "".join(rel_path_arr)           

    class Enum(object):
        def __init__(self, name, path):
            self.name = name
            self.path = path

    class Group(object):
        def __init__(self, tree):
            self.name = tree.find('name').text
            self.title = tree.find("title").text
            self.path = PATHS["HTML_SOURCE_PATH"] + tree.find('filename').text
            self.src_path = (PATHS["XML_SOURCE_PATH"] + tree.find('filename').text).replace(".html", ".xml")
            self.description = self.extract_description()
            self.functionList = []
            self.subgroup_names = []
            self.subgroups = []
            self.tags = []
            self.tags.append(strip_compound_name(self.name))
            self.prefix_content = None

        def extract_description(self):
            xml_tree = parse_xml(self.src_path)
            bs4 = BeautifulSoup()

            # use brief description if it exists
            description = markup_brief_description(bs4, xml_tree.find(r'compounddef'))

            # if not, use detailed description
            if not description:
                description = markup_description(bs4, xml_tree.find(r'compounddef'))

            # extract first sentence of description
            if description and description.text:
                first_sentence = description.text.split(". ")[0] + "."
                new_text = bs4.new_string(first_sentence)
                description.contents[0].replace_with(new_text)
            else:
                description = None

            return str(description) if str(description) else ""

        def add_function(self, fn_name, fn_obj):
            self.functionList.append(fn_obj)

            if not any(tag == fn_name for tag in self.tags):
                self.tags.append(fn_name)

    def add_function(self, ns, fn_name, fn_obj):
        self.functions[ns + "::" + fn_name] = fn_obj

    # searches the symbolMap for a given symbol, prepending cinder:: if not found as-is
    # returns a class
    def find_class(self, name):

        # replace leading ci:: with cinder:: instead
        searchname = str(name)
        if searchname.find("ci::") == 0:
            searchname = searchname.replace("ci::", "cinder::")

        # same key as name
        if searchname in self.classes:
            return self.classes[searchname]
        # key with "cinder::" prepended
        elif ("cinder::" + searchname) in self.classes:
            return self.classes["cinder::" + searchname]

        else:
            # iterate through all of the classes with namespace "cinder::" and test against just class name
            for className in self.classes:
                # if className has "cinder::" and namespace depth > 1, test against name
                if className.find("cinder") == 0 and len(className.split("::")) > 1:
                    testname = className.split("cinder::")[1].rsplit("::", 1)[-1]
                    if testname == searchname:
                        return self.classes[className]

            # check to see if the name is a typedef that is a shared_ptr to another class
            typedef = self.find_typedef(searchname)
            if typedef is not None:
                if typedef.sharedFrom is not None:
                    return typedef.sharedFrom
                else:
                    return typedef
                    # log("typedef " + typedef.name + " was not shared from an existing class", 1)

            # check to see if parent is a typedef
            searchname_parts = searchname.split("::")
            if len(searchname_parts) > 1:
                parent_name = searchname_parts[-2]
                typedef = self.find_typedef(parent_name)

                # if parent is typedef and has a sharedFrom property, find_class against that name
                if typedef and typedef.sharedFrom:
                    return self.find_class("::".join([typedef.sharedFrom.name, searchname_parts[-1]]))

            return None

    def find_namespace(self, name):

        searchname = str(name)
        if searchname.find("ci::") == 0:
            searchname = searchname.replace("ci::", "cinder::")

        # same key as name
        if searchname in self.namespaces.keys():
            return self.namespaces.get(searchname)

        # key with "cinder::" prepended
        elif ("cinder::" + searchname) in self.namespaces.keys():
            return self.namespaces["cinder::" + searchname]

        return None

    def find_group(self, name):
        return self.groups.get(name)

    def get_ordered_namespaces(self):
        """
        create an array of strings that include all of the namespaces and return
        :return: A list of namespace objects in alphabetical order
        """
        namespaces = []
        for nsKey in self.namespaces:
            ns = self.namespaces[nsKey]
            namespaces.append(ns)

        # sort by lowercased name
        namespaces = sorted(namespaces, key=lambda s: s.name.lower())

        return namespaces

    def get_whitelisted_namespaces(self):
        """
        create a list of namespace objects that consist of only whitelisted namespaces
        :return: An alphabetized list of namespace objects
        """
        namespaces = []
        for nsKey in self.namespaces:
            ns = self.namespaces[nsKey]

            # get whitelisted namespaces
            whitelisted = False
            if self.config.is_namespace_whitelisted(ns.name):
                whitelisted = True

            blacklisted = False
            if self.config.is_namespace_blacklisted(ns.name):
                blacklisted = True

            if whitelisted and not blacklisted:
                namespaces.append(ns)

        # sort by lowercased name
        namespaces = sorted(namespaces, key=lambda s: s.name.lower())
        return namespaces

    def find_typedef(self, name):
        searchname = str(name)
        if searchname.find("ci::") == 0:
            searchname = searchname.replace("ci::", "cinder::")

        # same key as name
        if searchname in self.typedefs.keys():
            return self.typedefs[searchname]

        # key with "cinder::" prepended
        elif ("cinder::" + searchname) in self.typedefs:
            return self.typedefs["cinder::" + searchname]

        # key with "glm::" prepended
        elif ("glm::" + searchname) in self.typedefs:
            return self.typedefs["glm::" + searchname]

        else:
            # iterate through all of the classes with namespace "cinder::" and test against just class name
            for typedef in self.typedefs:
                if typedef.find("cinder") == 0 and len(typedef.split("::")) > 1:
                    testname = typedef.split("cinder::")[1].rsplit("::", 1)[-1]
                    if testname == searchname:
                        return self.typedefs[typedef]
        return None


    def find_function(self, name, argstring=""):

        # find function name without namespace and parenthesis
        fn_name = strip_compound_name(name.split('(')[0])

        # find args and amt of args
        args = parse_arg_list(str(argstring))
        arg_len = len(args)

        # non-optional arguments for the function
        req_arg_len = 0
        for arg in args:
            if arg.find("=") < 0:
                req_arg_len += 1

        # find parent class first
        class_parts = name.split("(")[0].split("::")
        class_name = "::".join(class_parts[:-1])
        ref_obj = g_symbolMap.find_class(class_name)

        # if we can't find a matching function, try a namespace
        if ref_obj is None:
            ns_search = class_name
            if class_name == "":
                ns_search = "cinder"
            ref_obj = g_symbolMap.find_namespace(ns_search)

        # iterate through class/namespace functions
        fn_list = []
        if ref_obj:
            for fn in ref_obj.functionList:
                if fn.name == fn_name:
                    fn_list.append(fn)

        # try with cinder::app prefix
        # TODO: refactor a bit with the ability to whitespace different namespaces test
        if len(fn_list) is 0:
            ns_search = class_name
            if class_name == "":
                ns_search = "cinder::app"
            ref_obj = g_symbolMap.find_namespace(ns_search)

            # iterate through class/namespace functions
            if ref_obj:
                for fn in ref_obj.functionList:
                    if fn.name == fn_name:
                        fn_list.append(fn)

        # iterate through glm groups
        if len(fn_list) == 0:
            for group in self.groups:
                group_ref = self.groups[group]
                for fn in group_ref.functionList:
                    if fn.name == fn_name:
                        fn_list.append(fn)

        # else:
        #     for fn_key in self.functions:
        #         # print self.func
        #         # print self.functions[fn].name
        #         fn = self.functions[fn_key]
        #         if fn.name == fn_name:
        #             fn_list.append(fn)
        #             print "found match"
        #             print fn.args

        # no functions found in class or namespaces, try search by name
        if len(fn_list) == 0:
            fn_obj = self.functions.get(fn_name)
            fn_list.append(fn_obj)

        fn_index = 0
        # if we have a bunch of options, we want to whittle it down to the best one
        if len(fn_list) > 1:
            best_score = 0

            for idx, fn in enumerate(fn_list):
                # fn_arg_len = len(fn.args)
                score = 0

                # find amount of required arguments
                fn_arg_len = 0
                for arg in fn.args:
                    if arg.find("=") < 0:
                        fn_arg_len += 1

                # if number of passed in args is the same as this function's arg length, add to the score
                if arg_len == fn_arg_len:
                    score += 0.5

                # loop through the amount of args in this function
                fn_args = fn.args[0:fn_arg_len]
                if len(fn_args) > 0:
                    for i, arg in enumerate(fn_args):
                        if i + 1 > arg_len:
                            continue
                        ratio = (SM(None, arg, args[i]).ratio())
                        score += (ratio * 2.0)

                if score > best_score:
                    fn_index = idx
                    best_score = score

        found_function = fn_list[fn_index] if len(fn_list) > 0 else None
        return found_function

    def find_file(self, name):
        return self.files.get(name)

    def find_file_typedefs(self, name):
        return self.find_file(name).typedefs

    def find_enum(self, name):
        searchname = str(name)
        if searchname.find("ci::") == 0:
            searchname = searchname.replace("ci::", "cinder::")

        # enum_obj = None
        # if ns_obj is None:
        #     # find parent class first
        #     ns_parts = name.split("::")
        #     class_name = "::".join(ns_parts[:-1])
        #     class_obj = g_symbolMap.find_class(class_name)

        # same key as name
        if searchname in self.enums.keys():
            return self.enums.get(searchname)

        # key with "cinder::" prepended
        elif ("cinder::" + searchname) in self.enums:
            return self.enums.get("cinder::" + searchname)

    def get_class_ancestors(self, name):
        result = []
        existingclass = self.find_class(name)
        while existingclass and existingclass.base:
            result.insert(0, existingclass)
            existingclass = self.find_class(existingclass.base)

        if result:
            return result
        else:
            return []

    def get_class_descendants(self, name):
        result = []
        for aClass in self.classes:
            if self.classes[aClass].base == name:
                result.append(self.classes[aClass])

        if result:
            return result
        else:
            return []

    # def get_link_for_class(self, className):
    #     """ Get the link for the definition of a class.
    #         It may include namespace or not.
    #     """
    #     # strip down to the name of the class (without namespace)
    #     return ""

    def get_ordered_class_list(self):
        """ create an array of classes that include all of the classes and return
            the array in alphabetical order """
        classes = []
        for class_key in self.classes:
            class_obj = self.classes[class_key]
            classes.append(class_obj)

        # sort by lowercased name
        return sorted(classes, key=lambda s: s.name.lower())

    def find_classes_in_namespace(self, namespace, recursive=True):
        ns_classes = []
        for class_key in self.classes:
            if recursive:
                if class_key.startswith(namespace) > 0:
                    class_obj = self.find_class(class_key)
                    ns_classes.append(class_obj)
            else:
                class_pre = get_namespace(class_key)
                if namespace == class_pre:
                    class_obj = self.find_class(class_key)
                    ns_classes.append(class_obj)
        return ns_classes