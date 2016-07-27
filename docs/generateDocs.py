#! /usr/bin/python

"""
 Copyright (c) 2015, The Cinder Project, All rights reserved.

 This code is intended for use with the Cinder C++ library: http://libcinder.org

 Redistribution and use in source and binary forms, with or without modification, are permitted provided that
 the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and
	the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
	the following disclaimer in the documentation and/or other materials provided with the distribution.
z
 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
 WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
 PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
 ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
 TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
 NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 POSSIBILITY OF SUCH DAMAGE.

 AUTHOR: Greg Kepler | gkepler@gmail.com
"""

# -*- coding: utf-8 -*-
import sys
import re
import xml.etree.ElementTree as ET
import os
import shutil
import stat
import argparse
from difflib import SequenceMatcher as SM

# Third party in libs folder
sys.path.append("libs/")
sys.path.append("python/")
from bs4 import BeautifulSoup, Tag, NavigableString, Comment
from pystache.renderer import Renderer, Loader

import utils as utils
from utils import strip_compound_name, parse_xml, log, log_progress, path_join, LinkData
from symbol_map import SymbolMap, generate_symbol_map
import globals as g
from globals import PATHS, config
from bs4utils import *
import html_parser
from file_types import ClassFileData, GroupFileData, NamespaceFileData


parser = argparse.ArgumentParser(description='CiDocs')
parser.add_argument('path', nargs='?')
parser.add_argument('outpath', nargs='?')
parser.add_argument('-d', '--debug',
    action='store_true',
    help='show debug arguments')
parser.add_argument('-s', '--skiphtml',
    action='store_true',
    help='skip html generation')
parser.add_argument('--root',
    default=g.HTML_ROOT_DIR,
    help='server html root directory name')
parser.add_argument('--include-analytics',
    action='store_true',
    help='bool as to wheather to include analytics in frontend')




# # convert docygen markup to html markup
# tagDictionary = {
#     "linebreak": "br",
#     "emphasis": "em",
#     "ref": "a",
#     "ulink": "ulink",
#     "computeroutput": "code",
#     "includes": "span",
#     "simplesect": "span",
#     "para": "p"
# }



# ==================================================================================================== Utility functions



# def strip_compound_name(full_string):
#     ns_parts = full_string.split("::")
#     name = "".join(ns_parts[-1])
#     return name


# def parse_arg_list(arg_string):

#     # replace any commas in < and > enclosures with a temporary delim *** so that they
#     # don't get in the way when splitting args
#     arg_list = re.sub(r'(<\s\S*)(,)(\s\S* *>)', r'\1***\3', arg_string)
#     # split the args into a list
#     args = arg_list[1:-1].split(', ')

#     # strip white space
#     args = map(str.strip, args)
#     stripped_args = []

#     for indx, arg in enumerate(args):
#         is_optional = arg.find("=") > -1

#         # if there is more than one word, take the last one off
#         # if len(arg.split(" ")) > 1:
#         #     arg = " ".join(arg.split(" ")[:-1])

#         # we only want the new list to include required args
#         if not is_optional:
#             # replace the temp delimeter with a comma again
#             arg = arg.replace("***", ",")
#             stripped_args.append(arg)
#     # filter empty strings
#     stripped_args = filter(None, stripped_args)

#     return stripped_args

def get_namespace(full_string):
    ns_parts = full_string.split("::")
    prefix = "::".join(ns_parts[:-1])  # parent namespace up to last ::
    return prefix


# def add_class_to_tag(tag, class_name):
#     tag["class"] = tag.get("class", []) + [class_name]


# def gen_anchor_tag(bs4, anchor_name):
#     anchor = gen_tag(bs4, "a")
#     anchor["name"] = anchor_name
#     return anchor


# def gen_tag(bs4, tag_type, classes=None, contents=None):
#     """ Generates a new html element and optionally adds classes and content

#     Args:
#         bs4:        beautiful soup
#         tagType:    html tag/element (p, a, em, etc)
#         classes:    array of strings that you want as classes for the element
#         contents:   any content that you want to populate your tag with, if known
#     """

#     new_tag = bs4.new_tag(tag_type)

#     if classes:
#         for c in classes:
#             add_class_to_tag(new_tag, c)

#     if contents:
#         if type(contents) is list:
#             for c in contents:
#                 new_tag.append(clone(c))
#         else:
#             new_tag.append(contents)

#     return new_tag


# def gen_link_tag(bs4, text, link, target = "_self"):
#     link_tag = gen_tag(bs4, "a", [], text)
#     define_link_tag(link_tag, {"href": link})
#     link_tag["target"] = target
#     return link_tag


# def gen_rel_link_tag(bs4, text, link, src_dir, dest_dir):
#     """
#     Generates a link tag that was relative to the source directory, but should now be relative to the destination directory
#     :param bs4: beautifulsoup instance
#     :param text: text of link
#     :param link: relative link
#     :param src_dir: original source directory
#     :param dest_dir: destination source directory
#     :return: the link tag
#     """

#     # make sure they are dirs
#     src_dir = os.path.dirname(src_dir) + os.sep
#     dest_dir = os.path.dirname(dest_dir) + os.sep
#     new_link = relative_url(dest_dir, link)
#     link_tag = gen_link_tag(bs4, text, new_link)
#     return link_tag


# def replace_element(bs4, element, replacement_tag):
#     """
#     Replaces an html element with another one, keeping the text contents.
#     Use Case: Useful for replacing links with em tags or divs with spans
#     :param bs4: Beautiful Soup instance doing the work
#     :param element: element to change
#     :param replacement_tag: new element type to change to
#     :return:
#     """
#     if not element:
#         return

#     text_content = element.text
#     replacement = gen_tag(bs4, replacement_tag, None, text_content)
#     element.replace_with(replacement)


# def get_body_content(bs4):
#     return_str = ""
#     for content in bs4.body.contents:
#         content_utf = unicode(content).encode("utf-8", errors="replace")
#         content_str = content_utf.decode("utf-8", errors="replace")
#         if type(content) is Comment:
#             return_str += "<!-- " + content_str + "-->"
#         else:
#             return_str += content_str
#     return return_str


def extract_anchor(element):
    if element.attrib["id"]:
        return element.attrib["id"].split("_1")[-1]
    else:
        return None


# def define_link_tag(tag, attrib):
#     ref_id = None
#     href = None

#     if "refid" in attrib:
#         ref_id = attrib["refid"]
#         href = ref_id + ".html"

#     if "kindref" in attrib:
#         kind = attrib["kindref"]

#         if kind == "member":
#             str_list = ref_id.rsplit("_1", 1)
#             href = str_list[0] + ".html#" + str_list[1]

#     if "linkid" in attrib:
#         href = "../../include/cinder/" + attrib["linkid"]

#     if "href" in attrib:
#         href = attrib["href"]

#     if "typedef" in attrib:
#         data = attrib["typedef"]
#         file_name = data.find("anchorfile").text
#         anchor = data.find("anchor").text
#         href = file_name + "#" + anchor

#     if href is None:
#         log("DEFINING LINK TAG: " + str(tag), 1)
#     else:
#         tag["href"] = href


def parse_member_definition(bs4, member, member_name=None):
    """
    Parses a function tree and generates an object out of it
    :param bs4: beautifulsoup instance
    :param member: the member to parse
    :param member_name: the name of the class that's being parsed
    :return: the data object
    """
    if not member_name:
        member_name = member.find(r"name")
        member_name = member_name.text if member_name is not None else None

    anchor = utils.find_member_anchor(member)

    # return type
    return_div = gen_tag(bs4, "span")
    return_markup = iterate_markup(bs4, member.find(r"type"), return_div)

    # if id has a glm group key, replace link with <em>. The links are irrelevent atm
    if any(member.attrib["id"].find(group_key) > -1 for group_key in config.GLM_MODULE_CONFIG["group_keys"]):
        if return_markup:
            replace_element(bs4, return_markup.a, "em")

    return_str = str(return_markup)

    # get args
    argstring = member.find("argsstring")
    if argstring is None:
        argstring = member.find("arglist")
    argstring_text = argstring.text if argstring is not None else ""

    # description
    description_div = markup_description(bs4, member)
    description_str = str(description_div) if len(description_div.text) > 0 else None

    member_obj = {
        "name": member_name,
        "return": return_str,
        "anchor": anchor,
        "definition": {
            "name": member_name,
            "args": argstring_text
        },
        "description": description_str
    }

    return member_obj


def parse_function(bs4, member, class_name=None):

    member_name = member.find(r"name")
    member_name = member_name.text if member_name is not None else None
    is_constructor = False

    # determine if it is a constructor
    if class_name is not None:
        if member_name is not None and member_name == strip_compound_name(class_name):
            is_constructor = True

    member_obj = parse_member_definition(bs4, member, member_name)
    member_obj["is_constructor"] = is_constructor
    return member_obj


def parse_enum(bs4, member):

    member_obj = parse_member_definition(bs4, member)
    values = []
    for val in member.findall("enumvalue"):
        enum_name = val.find("name").text
        values.append({"name": enum_name})

    member_obj["values"] = values
    member_obj["return"] = "enum"
    return member_obj




def find_typedefs_of(class_name, typedef_list):
    """
    Finds typedef objects that are shared from the given class within a given namespace
    :return: list if SymbolMap.Typedef objects
    """
    typedefs = []
    class_name = strip_compound_name(class_name)
    
    for typedef in typedef_list:
        if typedef.sharedFrom:
            if typedef.sharedFrom.name == class_name:
                typedefs.append(typedef)
    return typedefs


# ============================================================================================ File Processing Functions


def process_xml_file_definition(in_path, out_path, file_type):
    """
    Process an xml file definition, such as a class, namespace, or group
    :param in_path: xml file location
    :param out_path: final html file location
    :param file_type: "class", "namespace", or "group"
    :return:
    """

    # we dont like files that start with '_'
    if os.path.basename(in_path).startswith("_"):
        return

    # define the tree that contains all the data we need to populate this page
    tree = parse_xml(in_path)

    if tree is None:
        return

    if file_type == "class":
        if any(in_path.find(blacklisted) > -1 for blacklisted in config.CLASS_LIST_BLACKLIST):
            log("Skipping file | Class " + in_path + " blacklisted", 0)
            return

        html_template = config.CLASS_TEMPLATE
        file_data = fill_class_content(tree)
        section = "classes"
        body_class = "classes"

    elif file_type == "namespace":
        html_template = config.NAMESPACE_TEMPLATE
        file_data = fill_namespace_content(tree)

        if not file_data:
            return

        section = "namespaces"
        body_class = "namespaces"

    elif file_type == "module":
        html_template = config.GROUP_TEMPLATE
        file_data = fill_group_content(tree, config.GLM_MODULE_CONFIG)
        section = "reference"
        body_class = "reference"
    else:
        log("Skipping " + in_path, 1)
        return

    log_progress('Processing file: ' + str(in_path))

    # Generate the html file from the template and inject content
    file_content = file_data.get_content()
    bs4 = render_template(html_template, file_content)
    content_dict = {
        "page_title": file_content["title"],
        "main_content": get_body_content(bs4),
        "body_class": body_class,
        "section_namespace": "cinder",
        str("section_" + section): "true"}
    # append file meta
    content_dict.update(g.meta.copy())

    # render within main template
    bs4 = render_template(os.path.join(PATHS["TEMPLATE_PATH"], "master-template.mustache"), content_dict)
    # make sure all links are absolute
    utils.update_links_abs(bs4, PATHS["TEMPLATE_PATH"])

    if not bs4:
        log("Skipping class due to something nasty. Bother Greg and try again some other time. Error rendering: " + in_path, 2)
        return

    # print output
    # update links in the template
    utils.update_links(bs4, PATHS["TEMPLATE_PATH"] + "htmlContentTemplate.html", PATHS["TEMPLATE_PATH"], out_path)

    # replace any code chunks with <pre> tags, which is not possible on initial creation
    replace_code_chunks(bs4)

    # link up all ci tags
    for tag in bs4.find_all('ci'):
        process_ci_tag(bs4, tag, in_path, out_path)

    # add to search index
    link_path = gen_rel_link_tag(bs4, "", out_path, PATHS["HTML_SOURCE_PATH"], PATHS["HTML_DEST_PATH"])["href"]
    g.search_index.add(bs4, link_path, file_data.kind, file_data.search_tags)

    # deactivate invalid relative links
    for link in bs4.find_all("a"):
        if link.has_attr("href") and link["href"].startswith("_"):
            # replace <a> with <span>
            dead_tag = gen_tag(bs4, "span", None, link.string)
            link.replace_with(dead_tag)

    # write the file
    utils.write_html(bs4, out_path)


def parse_namespaces(tree, sections):
    namespaces = []
    if config.is_section_whitelisted(sections, "namespaces"):
        for member in tree.findall(r"compounddef/innernamespace"):
            link = path_join(PATHS["HTML_DEST_PATH"], member.attrib["refid"] + ".html")
            link_data = LinkData(link, member.text)
            namespaces.append(link_data)
    return namespaces


def parse_classes(tree, sections):
    classes = []
    if config.is_section_whitelisted(sections, "classes"):
        for member in tree.findall(r"compounddef/innerclass[@prot='public']"):
            link = member.attrib["refid"] + ".html"
            rel_link = path_join(PATHS["HTML_DEST_PATH"], link)
            link_data = LinkData(rel_link, member.text)

            kind = "struct" if link.startswith("struct") else "class"
            class_obj = {
                "link_data": link_data,
                "kind": kind
            }
            classes.append(class_obj)
    return classes


def parse_typedefs(bs4, tree, sections):
    typedefs = []

    if config.is_section_whitelisted(sections, "typedefs"):
        section_config = config.get_section_config(sections, "typedefs")
        if section_config:
            prefix_blacklist = section_config["prefix_blacklist"] if section_config.has_key("prefix_blacklist") else None
        else:
            prefix_blacklist = None

        for member in tree.findall(r"compounddef/sectiondef/[@kind='typedef']/memberdef/[@kind='typedef']"):
            member_name = member.find(r"name").text
            if prefix_blacklist and any(member_name.startswith(blacklisted) > 0 for blacklisted in prefix_blacklist):
                # skip this blacklisted typedef
                continue

            typedef_obj = parse_member_definition(bs4, member)
            typedefs.append(typedef_obj)
    return typedefs


def parse_enums(bs4, tree, sections):
    enums = []
    if config.is_section_whitelisted(sections, "enums"):
        for member in tree.findall(r"compounddef/sectiondef/[@kind='enum']/memberdef/[@kind='enum']"):
            member_obj = parse_enum(bs4, member)
            enums.append(member_obj)
    return enums


def parse_functions(bs4, tree, sections):
    fns = []
    if config.is_section_whitelisted(sections, "functions"):
        for member in tree.findall(r"compounddef/sectiondef/[@kind='func']/memberdef/[@kind='function']"):
            function_obj = parse_member_definition(bs4, member)
            fns.append(function_obj)
    return fns


def parse_free_functions(bs4, tree, sections):
    free_fns = []
    if config.is_section_whitelisted(sections, "free_functions"):
        for member in tree.findall(r"compounddef/sectiondef/[@kind='user-defined']/memberdef/[@kind='function']"):
            function_obj = parse_member_definition(bs4, member)
            free_fns.append(function_obj)
    return free_fns


def parse_vars(bs4, tree, sections):
    variables = []
    if config.is_section_whitelisted(sections, "variables"):
        for member in tree.findall(r"compounddef/sectiondef/[@kind='var']/memberdef/[@kind='variable']"):
            var_obj = parse_member_definition(bs4, member)
            initializer = member.find('initializer').text if member.find('initializer') is not None else None
            var_obj["definition"]["args"] = initializer
            variables.append(var_obj)
    return variables


def fill_class_content(tree):
    """
    Populates the class content object with data
    :param tree:
    :return:
    """

    bs4 = BeautifulSoup()
    file_data = ClassFileData(tree)

    include_file = ""
    include_path = ""
    include_tag = tree.find(r"compounddef/includes")
    location_tag = tree.find(r"compounddef/location")
    if location_tag is not None:
        include_path = "/".join(location_tag.attrib["file"].split("/")[1:])
    if include_tag is not None:
        include_file = include_tag.text
    class_name = file_data.name
    file_def = g.symbolsMap.find_file(include_file)
    class_def = g.symbolsMap.find_class(class_name)

    # class template stuff ------------------------------ #
    file_data.is_template = True if tree.find(r"compounddef/templateparamlist") is not None else False
    if file_data.is_template:
        try:
            def_name = tree.find(r"compounddef/templateparamlist/param/type")
            file_data.template_def_name = def_name.text if def_name is not None else ""
        except Exception as e:
            file_data.template_def_name = ""
            log(e.message, 1)

    if not class_def:
        log("NO CLASS OBJECT DEFINED FOR: " + class_name, 1)
        # raise
        # return

    # page title ---------------------------------------- #
    file_data.title = file_data.name

    # add namespace nav --------------------------------- #
    file_data.namespace_nav = str(g.namespace_nav)

    # page header --------------------------------------- #
    file_data.page_header = file_data.compoundName

    # add description ----------------------------------- #
    description = markup_description(bs4, tree.find(r'compounddef'))
    file_data.description = str(description) if description is not None else ""

    # includes ------------------------------------------ #
    include_link = None
    if include_file and include_path:
        file_obj = g.symbolsMap.find_file(include_file)
        github_path = config.GITHUB_PATH + '/include/' + include_path
        if file_obj:
            include_link = LinkData(github_path, include_path)

    file_data.includes = include_link

    # typedefs ------------------------------------------ #
    typedefs = []
    ns_obj = g.symbolsMap.find_namespace(file_data.namespace)
    if ns_obj and ns_obj.typedefs:
        class_typedefs = find_typedefs_of(class_name, ns_obj.typedefs)
        if file_def is not None:
            for t in class_typedefs:
                link_data = LinkData()
                link_data.label = t.name
                link_path = path_join(PATHS["HTML_DEST_PATH"], t.path)
                link_data.link = link_path
                typedefs.append(link_data)
    file_data.typedefs = typedefs

    # class hierarchy ----------------------------------- #
    if class_def:
        class_hierarchy = gen_class_hierarchy(bs4, class_def)
        file_data.class_hierarchy = str(class_hierarchy) if class_hierarchy else None

    # class list ---------------------------------------- #
    classes = []
    for classDef in tree.findall(r"compounddef/innerclass[@prot='public']"):
        link_data = LinkData()
        link_data.label = strip_compound_name(classDef.text)
        link_data.link = path_join(PATHS["HTML_DEST_PATH"], classDef.attrib["refid"] + ".html")
        classes.append(link_data)
    file_data.classes = classes

    # related links  ------------------------------------ #
    # generated by guides and references
    related = []
    if class_def:
        if class_def.relatedLinks:
            for link_data in class_def.relatedLinks:
                related.append(link_data)

        # ci prefix / description ----------------------- #
        # if the class has a prefix, add it here
        if class_def.prefix_content:
            file_data.prefix = class_def.prefix_content

    file_data.related = related

    # enumerations -------------------------------------- #
    enumerations = []
    for e in tree.findall(r"compounddef/sectiondef/memberdef[@kind='enum']"):
        member_obj = parse_enum(bs4, e)
        enumerations.append(member_obj)
    file_data.enumerations = enumerations

    # TODO: Look into and re-evaluate if this is needed or not since the definitions are all over the map and may be an edge case
    # public types -------------------------------------- #
    # public_types = []
    # # for member in tree.findall(r"compounddef/sectiondef/memberdef[@kind='typedef']"):
    # for member in tree.findall(r"compounddef/sectiondef[@kind='public-type']/memberdef[@prot='public']"):
    #
    #     member_obj = None
    #     print member.attrib["kind"]
    #     if member.attrib["kind"] == "enum":
    #         member_obj = parse_member_definition(bs4, member)
    #         member_obj["return"] = "enum"
    #         enum_link = gen_link_tag(bs4, member_obj["name"], "#"+find_member_anchor(member))
    #         member_obj["definition"]["name"] = str(enum_link)
    #     else:
    #         member_obj = parse_function(bs4, member, class_name)
    #     print member.attrib["kind"]
    #     print member.find("name").text
    #
    #     if member_obj is None:
    #         continue
    #
    #     public_types.append(member_obj)
    #
    # file_data.public_types = public_types

    # public member Functions --------------------------- #
    public_fns = []
    public_static_fns = []
    for memberFn in tree.findall(r'compounddef/sectiondef/memberdef[@kind="function"][@prot="public"]'):

        function_obj = parse_function(bs4, memberFn, class_name)
        is_static = memberFn.attrib["static"]

        if is_static == 'yes':
            public_static_fns.append(function_obj)
        else:
            public_fns.append(function_obj)

    file_data.public_functions = public_fns
    file_data.public_static_functions = public_static_fns

    # protected member functions ------------------------ #
    protected_functions = []
    for member in tree.findall(r'compounddef/sectiondef/memberdef[@kind="function"][@prot="protected"]'):
        function_obj = parse_function(bs4, member, class_name)
        protected_functions.append(function_obj)
    file_data.protected_functions = protected_functions

    # protected attributes ------------------------------ #
    protected_attrs = []
    for v in tree.findall(r'compounddef/sectiondef/memberdef[@kind="variable"][@prot="protected"]'):
        member_obj = parse_member_definition(bs4, v)
        protected_attrs.append(member_obj)
    file_data.protected_attrs = protected_attrs

    # friends ------------------------------------------- #
    friends = []
    for member in tree.findall(r'compounddef/sectiondef/memberdef[@kind="friend"]'):
        member_obj = parse_member_definition(bs4, member)

        # replace name with link to class
        friend_class = g.symbolsMap.find_class(member_obj["name"])

        # link up friend, if class exists
        if friend_class:
            friend_link = gen_rel_link_tag(bs4, friend_class.name, friend_class.path, PATHS["TEMPLATE_PATH"], PATHS["HTML_DEST_PATH"])
            member_obj["definition"]["name"] = str(friend_link)
        friends.append(member_obj)
    file_data.friends = friends

    if class_def:
        file_data.search_tags = class_def.tags

    return file_data


def fill_namespace_content(tree):

    bs4 = BeautifulSoup()

    if tree is None:
        return

    # get common data for the file
    file_data = NamespaceFileData(tree)
    ns_def = g.symbolsMap.find_namespace(file_data.name)

    if ns_def:
        if config.is_namespace_blacklisted(ns_def.name):
            log("Skipping file | Namespace " + ns_def.name + " blacklisted", 1)
            return
    else:
        log("Skipping: tree is not defined", 1)
        return

    # return result of special glm namespace content filling
    # TODO: If we get here, that means the namespace is NOT blacklisted, so this is where we check if each piece is whitelisted, if that array is empty, we assume that it's all whitelisted
    ns_config = config.get_ns_config(ns_def.name)
    if ns_config and ns_config.has_key("structure_whitelist"):
        sections = ns_config["structure_whitelist"]
    else:
        sections = None

    # if ns_def.name == "glm":
    #     return fill_glm_namespace_content(tree)

    # page title ---------------------------------------- #
    file_data.title = file_data.name

    # add namespace nav --------------------------------- #
    file_data.namespace_nav = str(g.namespace_nav)

    # add namespaces ------------------------------------ #
    file_data.namespaces = parse_namespaces(tree, sections)

    # add classes --------------------------------------- #
    file_data.classes = parse_classes(tree, sections)

    # add typedefs -------------------------------------- #
    file_data.typedefs = parse_typedefs(bs4, tree, sections)

    # add enumerations ---------------------------------- #
    file_data.enumerations = parse_enums(bs4, tree, sections)

    # functions ----------------------------------------- #
    file_data.functions = parse_functions(bs4, tree, sections)

    # free functions ------------------------------------ #
    file_data.free_functions = parse_free_functions(bs4, tree, sections)

    # variables ----------------------------------------- #
    file_data.variables = parse_vars(bs4, tree, sections)

    # define search tags
    if ns_def:
        file_data.search_tags = ns_def.tags
    else:
        file_data.search_tags = []

    file_data.search_tags.extend(["namespace"])

    return file_data


def fill_group_content(tree, module_config):
    bs4 = BeautifulSoup()
    file_data = GroupFileData(tree, module_config)

    group_name = file_data.name
    group_def = g.symbolsMap.find_group(group_name)

    if not group_def:
        log("NO CLASS OBJECT DEFINED FOR: " + group_name, 1)
        # return

    # page title ---------------------------------------- #
    file_data.title = file_data.name

    # page header --------------------------------------- #
    file_data.page_header = file_data.name

    # add description ----------------------------------- #
    description = markup_description(bs4, tree.find(r'compounddef'))
    file_data.description = str(description) if description is not None else ""

    # submodules ---------------------------------------- #
    subgroups = []
    if group_def is not None:
        for subgroup in group_def.subgroups:
            subgroup_obj = {
                "label": subgroup.name,
                "link": subgroup.path
            }
            subgroups.append(subgroup_obj)
    file_data.subgroups = subgroups

    # typedefs ------------------------------------------ #
    typedefs = []
    for member in tree.findall(r"compounddef/sectiondef/[@kind='typedef']/memberdef/[@kind='typedef']"):
        typedef_obj = parse_member_definition(bs4, member)
        typedefs.append(typedef_obj)
    file_data.typedefs = typedefs

    # ci prefix / description --------------------------- #
    # if the group has a prefix, add it here
    if group_def is not None:
        if group_def.prefix_content is not None:
            file_data.prefix = group_def.prefix_content

    # # enumerations -------------------------------------- #
    # enumerations = []
    # for e in tree.findall(r"compounddef/sectiondef/memberdef[@kind='enum']"):
    #     member_obj = parse_enum(bs4, e)
    #     enumerations.append(member_obj)
    # file_data.enumerations = enumerations

    # public member Functions --------------------------- #
    public_fns = []
    public_static_fns = []
    for memberFn in tree.findall(r'compounddef/sectiondef/memberdef[@kind="function"][@prot="public"]'):

        function_obj = parse_function(bs4, memberFn, group_name)
        is_static = memberFn.attrib["static"]

        if is_static == 'yes':
            public_static_fns.append(function_obj)
        else:
            public_fns.append(function_obj)

    file_data.public_functions = public_fns
    file_data.public_static_functions = public_static_fns

    if group_def:
        file_data.search_tags = group_def.tags

    return file_data



# =============================================================================================== File Utility Functions



# def write_search_index():
#     # save search index to js file
#     document = "var search_index_data = " + json.dumps(g.g_search_index).encode('utf-8')
#     # print document
#     if not os.path.exists(os.path.dirname(PATHS["HTML_DEST_PATH"] + 'search_index.js')):
#         os.makedirs(os.path.dirname(PATHS["HTML_DEST_PATH"] + 'search_index.js'))
#     with codecs.open(PATHS["HTML_DEST_PATH"] + 'search_index.js', "w", "UTF-8") as outFile:
#         outFile.write(document)


# def add_to_search_index(html, save_path, search_type, tags=[]):
#     """
#     Adds the html page to the search index
#     :param html:
#     :param save_path:
#     :param search_type:
#     :param tags:
#     :return:
#     """
#     # global g_search_index
#     if not g.g_search_index:
#         g.g_search_index = {"data": []}

#     # creates new list from tags minus any dupes
#     search_list = list(set(tags))

#     search_obj = {"id": None, "title": None, "tags": []}
#     search_obj["id"] = len(g.g_search_index["data"])
#     search_obj["title"] = html.head.find("title").text if html.head.find("title") else ""
#     search_obj["link"] = save_path
#     search_obj["tags"] = search_list
#     search_obj["type"] = search_type
#     g.g_search_index["data"].append(search_obj)


def get_file_type(file_prefix):
    """
    Determines the file type based on the file prefix
    :param file_prefix: prefix in file name
    :return: string indicating the type of file to parse
    """
    if is_class_type(file_prefix):
        return "class"
    elif is_namespace_type(file_prefix):
        return "namespace"
    elif is_module_type(file_prefix):
        return "module"


def is_class_type(class_str):
    """
    Tests whether the filename is a class type
    :param class_str:
    :return: Boolean
    """
    if any([class_str.startswith(prefix) for prefix in config.CLASS_FILE_PREFIXES]):
        return True
    return False


def is_namespace_type(ns_str):
    """
    Tests whether the filename is a namespace type
    :param class_str:
    :return: ns_str
    """
    if any([ns_str.startswith(prefix) for prefix in config.NAMESPACE_FILE_PREFIXES]):
        return True
    return False


def is_module_type(module_str):
    """
    Tests whether the filename is a group type
    :param module_str:
    :return: Boolean
    """
    if any([module_str.startswith(prefix) for prefix in config.GROUP_FILE_PREFIXES]):
        return True
    return False


def process_file(in_path, out_path=None):
    """ Generate documentation for a single file

        Args:
            inPath: The file to process
            outPath: The file to save the generated html file to
    """

    file_path = in_path
    file_prefix = utils.get_file_prefix(file_path)
    is_html_file = True if utils.get_file_extension(file_path).lower() == ".html" else False
    is_xml_file = True if utils.get_file_extension(file_path).lower() == ".xml" else False

    if is_html_file:
        file_path = os.sep.join(in_path.split('htmlsrc'+os.sep)[1:])
        save_path = out_path if out_path is not None else PATHS["HTML_DEST_PATH"] + file_path
    else:
        save_path = out_path if out_path is not None else PATHS["HTML_DEST_PATH"] + utils.get_file_prefix(in_path) + ".html"

    if is_html_file:
        # print "process: " + PATHS["HTML_SOURCE_PATH"] + file_path
        html_parser.process_html_file(PATHS["HTML_SOURCE_PATH"] + file_path, save_path)

    elif is_xml_file:
        file_type = get_file_type(file_prefix)
        # process html directory always, since they may generate content for class or namespace reference pages
        if not g.state.processed_html_files and not g.args.skiphtml:
            process_html_dir(PATHS["HTML_SOURCE_PATH"])

        process_xml_file_definition(in_path, os.path.join(PATHS["HTML_DEST_PATH"], save_path), file_type)


def process_dir(in_path, out_path):
    """ Iterates a directory and generates documentation for each xml file
        in the directory as long as it is a class, struct or namespace

        Args:
            inPath: The directory to process
            outPath: The directory to save the generated html file to
    """

    for file_path in os.listdir(in_path):
        full_path = os.path.join(in_path, file_path)
        # if file_path.endswith(".xml"):

        if os.path.isfile(full_path):
            process_file(full_path)

        elif os.path.isdir(full_path):
            process_html_dir(full_path)


def process_html_dir(in_path):
    # global state

    for path, subdirs, files in os.walk(in_path):
        path_dir = path.split(os.sep)[-1]
        if path_dir == "_templates" or path_dir == "assets":
            continue
        for name in files:
            # file_prefix = utils.get_file_prefix(name)
            file_ext = utils.get_file_extension(name).lower()
            if file_ext == ".html":

                if path.endswith(os.sep):
                    src_path = path[:-1]
                else:
                    src_path = path

                src_path = src_path + os.sep + name
                process_file(src_path)

    # add subnav for all guides that need them
    # process_sub_nav()

    g.state.processed_html_files = True


# def copyFiles( HTML_SOURCE_PATH, DOXYGEN_HTML_PATH ):
def copy_files():
    src = PATHS["HTML_SOURCE_PATH"]
    dest = PATHS["HTML_DEST_PATH"]

    try:
        copytree(src, dest, ignore=shutil.ignore_patterns("_templates*", "*.html"))
    except OSError as e:
        log('Directory not copied. Error:' + str(e))


# from http://stackoverflow.com/a/22331852/680667
def copytree(src, dst, symlinks=False, ignore=None):
    """ Copies all of the files from the source directory
        to a destination directory. Pass in anything that should be ignored.
    """

    if not os.path.exists(dst):
        os.makedirs(dst)
        shutil.copystat(src, dst)
    lst = os.listdir(src)

    # make list of files and directories minus the ignored stuff
    if ignore:
        excl = ignore(src, lst)
        lst = [x for x in lst if x not in excl]

    for item in lst:
        s = os.path.join(src, item)
        d = os.path.join(dst, item)

        if symlinks and os.path.islink(s):
            if os.path.lexists(d):
                os.remove(d)
                os.symlink(os.readlink(s), d)
            try:
                st = os.lstat(s)
                mode = stat.S_IMODE(st.st_mode)
                os.lchmod(d, mode)
            except:
                pass  # lchmod not available
        elif os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def parse_metadata():

    # meta will use docs_meta as a base and adjust from there
    meta = g.meta.copy()

    # load meta file
    meta_file = parse_xml(config.PROJECT_META_FILE)
    
    # get doxygen version
    meta["doxy_version"] = meta_file.attrib.get("version")

    # get cinder version
    for member in meta_file.findall(r'compounddef/sectiondef/memberdef[@kind="define"]'):
        if member.find(r"name").text == "CINDER_VERSION_STR":
            ver = str(member.find(r"initializer").text)
            ver = ver.replace('"', "")
            meta["cinder_version"] = ver

    # get docs directory
    meta["docs_root"] = g.args.root

    # include google analytics
    meta["include_analytics"] = g.args.include_analytics

    return meta;
        

if __name__ == "__main__":
    """ Main Function for generating html documentation from doxygen generated xml files

    Args:
        -   No arguments generates all Cinder docs. Expects Doxygen to have been run previously.
        -   Can pass in a single xml file to process by passing in path to xml file
            and optionally, the resulting html file.
            if no out path is supplied, outputs to DOXYGEN_HTML_PATH
            Ex: python xmlToHtml.py xml/classcinder_1_1_surface_t.xml
        -   Can alternatively pass in a directory to process by providing the xml directory
            Ex: python xmlToHtml.py xml/ html/
    """

    g.args = parser.parse_args()
    print parser.parse_args()

    # Make sure we're compiling using pythong 2.7.6+
    version_info = sys.version_info

    #if version_info.major >= 2 and version_info.minor >= 7 and version_info.micro < 6:
    #    sys.exit("ERROR: Sorry buddy, you must use python 2.7.6+ to generate documentation. Visit https://www.python.org/downloads/ to download the latest.")
    # if sys.version

    if g.args.path:
        inPath = g.args.path
        if not os.path.isfile(inPath) and not os.path.isdir(inPath):
            log("Nice try! Directory or file '" + inPath + "' doesn't even exist, so we're going to stop right... now!", True)
            quit()

    if not os.path.exists(PATHS["TAG_FILE_PATH"]):
        log("I got nothin' for you. The tag file [" + PATHS["TAG_FILE_PATH"] + "] doesn't exist yet. "
            "Run Doxygen first and try me again later.", 2, True)
        quit()

    # load meta data
    g.meta = parse_metadata();

    # Load tag file
    log("parsing tag file", 0, True)
    # g_tag_xml = ET.ElementTree(ET.parse(PATHS["TAG_FILE_PATH"]).getroot())
    # generate symbol map from tag file
    g.symbolsMap = generate_symbol_map()

    # copy files from htmlsrc/ to html/
    log("copying files", 0, True)
    copy_files()

    # generate namespace navigation
    g.namespace_nav = generate_namespace_nav()

    log("processing files", 0, True)
    if not g.args.path: # no args; run all docs
        # process_html_dir(PATHS["HTML_SOURCE_PATH"], "html/")
        process_dir("xml" + os.sep, "html" + os.sep)

        # save search index to json file
        g.search_index.write()
        log("SUCCESSFULLY GENERATED CINDER DOCS!", 0, True)
        # quit()
    elif g.args.path:
        inPath = g.args.path
        # process a specific file
        if os.path.isfile(inPath):
            process_file(inPath, g.args.outpath if len(sys.argv) > 2 else None)
            log("SUCCESSFULLY GENERATED YOUR FILE!", 0, True)
        elif os.path.isdir(inPath):
            if inPath == "htmlsrc" + os.sep:
                process_html_dir(PATHS["HTML_SOURCE_PATH"])
            else:
                process_dir(inPath, "html" + os.sep)
            log("SUCCESSFULLY GENERATED YOUR FILES!", 0, True)
    else:
        log("Unknown usage", 1, True)
