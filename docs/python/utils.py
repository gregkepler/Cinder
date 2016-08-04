#! /usr/bin/python
import os
import sys
import re
import codecs
import bs4utils
import xml.etree.ElementTree as ET
import globals as g
from globals import PATHS, config
import posixpath
from posixpath import join as urljoin
from bs4 import BeautifulSoup, Tag
# from pystache.renderer import Renderer, Loader
# from globals import args
from difflib import SequenceMatcher as SM


# =============================================================================================== Logging

def log(message, level=0, force=False):   
    if g.args.debug or force:

        if level == 0 or not level:
            message_prefix = "INFO"
        elif level == 1:
            message_prefix = "WARNING"
        elif level == 2:
            message_prefix = "ERROR"
            print message_prefix
            print str(message)

        print("\r    *** " + message_prefix + ": [ " + message + " ] ***")

def log_progress(message):
    sys.stdout.write('\r' + str(message))
    sys.stdout.write("\033[K")
    sys.stdout.flush()


# =============================================================================================== Utilities

def strip_compound_name(full_string):
    ns_parts = full_string.split("::")
    name = "".join(ns_parts[-1])
    return name

def parse_arg_list(arg_string):

    # replace any commas in < and > enclosures with a temporary delim *** so that they
    # don't get in the way when splitting args
    arg_list = re.sub(r'(<\s\S*)(,)(\s\S* *>)', r'\1***\3', arg_string)
    # split the args into a list
    args = arg_list[1:-1].split(', ')

    # strip white space
    args = map(str.strip, args)
    stripped_args = []

    for indx, arg in enumerate(args):
        is_optional = arg.find("=") > -1

        # if there is more than one word, take the last one off
        # if len(arg.split(" ")) > 1:
        #     arg = " ".join(arg.split(" ")[:-1])

        # we only want the new list to include required args
        if not is_optional:
            # replace the temp delimeter with a comma again
            arg = arg.replace("***", ",")
            stripped_args.append(arg)
    # filter empty strings
    stripped_args = filter(None, stripped_args)

    return stripped_args


def relative_url(in_path, link):
    """
    Generates a relative url from a absolute destination directory 
    to an absolute file path
    """

    index = 0
    SEPARATOR = "/"
    d = filter(None, in_path.replace('\\', SEPARATOR).split( SEPARATOR ))
    s = filter(None, link.replace('\\', SEPARATOR).split( SEPARATOR ))

    # FIND largest substring match
    for i, resource in enumerate( d ):
        if resource != s[i]:
            break
        index += 1

    # remainder of source
    s = s[index:]
    
    backCount = len( d ) - index

    path = "../" * backCount
    path += SEPARATOR.join( s )
    return path


def path_join(path, link):
    p = path.replace('\\', '/')
    l = link.replace('\\', '/')
    sep = '/' if not p.endswith('/') else ''
    new_link = p + sep + l
    return new_link


def get_namespace(full_string):
    ns_parts = full_string.split("::")
    prefix = "::".join(ns_parts[:-1])  # parent namespace up to last ::
    return prefix


def extract_anchor(element):
    if element.attrib["id"]:
        return element.attrib["id"].split("_1")[-1]
    else:
        return None


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

    anchor = find_member_anchor(member)

    # return type
    return_div = bs4utils.gen_tag(bs4, "span")
    return_markup = bs4utils.iterate_markup(bs4, member.find(r"type"), return_div)

    # if id has a glm group key, replace link with <em>. The links are irrelevent atm
    if any(member.attrib["id"].find(group_key) > -1 for group_key in config.GLM_MODULE_CONFIG["group_keys"]):
        if return_markup:
            bs4utils.replace_element(bs4, return_markup.a, "em")

    return_str = str(return_markup)

    # get args
    argstring = member.find("argsstring")
    if argstring is None:
        argstring = member.find("arglist")
    argstring_text = argstring.text if argstring is not None else ""

    # description
    description_div = bs4utils.markup_description(bs4, member)
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


# ======================================================================================================== Link Updating


def get_path_dir(path):
    path_parts = path.replace('\\', '/').split('/')
    # if it doesn't end with a '/', lop off the last word
    if not path.endswith('/'):
        in_dir = '/'.join(path_parts[:-1]) + '/'
    else:
        in_dir = path
    return in_dir

def update_links_abs(html, src_path):
    """
    Replace all of the relative a links with absolut links
    :param html:
    :param src_path:
    :param dest_path:
    :return:
    """

    # css links
    for link in html.find_all("link"):
        if link.has_attr("href"):
            link["href"] = update_link_abs(link["href"], src_path)

    # a links
    for a in html.find_all("a"):
        if a.has_attr("href"):
            link_href = a["href"]

            # if the link is an hpp file, lets link to the github link since we likely don't have it in our docs
            if link_href.find(config.GLM_MODULE_CONFIG["source_file_ext"]) > -1:
                a["href"] = config.GLM_MODULE_CONFIG["url_prefix"] + a.text
            else:
                a["href"] = update_link_abs(a["href"], src_path)

    # script links
    for script in html.find_all("script"):
        if script.has_attr("src"):
            script["src"] = update_link_abs(script["src"], src_path)

    # images
    for img in html.find_all("img"):
        if img.has_attr("src"):
            img["src"] = update_link_abs(img["src"], src_path)

    # iframes
    for iframe in html.find_all("iframe"):
        if iframe.has_attr("src"):
            link_src = iframe["src"]
            if link_src.startswith('javascript') or link_src.startswith('http'):
                return

            new_link = update_link_abs(link_src, src_path)
            iframe["src"] = new_link


# def relative_url(in_path, link):
#     """
#     Generates a relative url from a absolute destination directory 
#     to an absolute file path
#     """

#     index = 0
#     SEPARATOR = "/"
#     d = filter(None, in_path.replace('\\', SEPARATOR).split( SEPARATOR ))
#     s = filter(None, link.replace('\\', SEPARATOR).split( SEPARATOR ))

#     # FIND largest substring match
#     for i, resource in enumerate( d ):
#         if resource != s[i]:
#             break
#         index += 1

#     # remainder of source
#     s = s[index:]
    
#     backCount = len( d ) - index

#     path = "../" * backCount
#     path += SEPARATOR.join( s )
#     return path


def update_link_abs(link, in_path):
    """
    Update the given link to point to something relative to the new path
    :param link: The link to change
    :param in_path: the original path to the file that the link lives in
    :return:
    """

    if link.startswith("http") or link.startswith("javascript:") or link.startswith("#"):
        return link

    SEPARATOR = "/"
    in_path = in_path.replace('\\', SEPARATOR)

    index = 0
    backs = 0
    # SPLIT the url into a list of path parts
    r = in_path.split(SEPARATOR)
    r = filter(None, r)
    l = link.split(SEPARATOR)
    l = filter(None, l)

    # FIND largest substring match
    for i, resource in enumerate( r ):
        if resource != l[i]:
            break
        index += 1

    # FIND the amount of back references
    for j, back_ref in enumerate( l ):
        if back_ref != "..":
            break
        backs += 1

    if not index:
        if backs > 0:
            final = SEPARATOR.join(r[:backs*-1]) + SEPARATOR + SEPARATOR.join(l[backs:]) 
        else:
            final = SEPARATOR.join(r) + SEPARATOR + SEPARATOR.join(l)
    else:
        pre = r[:index]
        post = l[index:]
        final = SEPARATOR.join(pre) + SEPARATOR + SEPARATOR.join(post)

    return final    


def update_links(html, template_path, src_path, save_path):
    """
    Replace all of the relative a links, js links and image links and make them relative to the outpath
    :param html:
    :param template_path:
    :param dest_path:
    :return:
    """

    template_path = "/".join(template_path.replace('\\', '/').split('/'))

    # css links
    for link in html.find_all("link"):
        if link.has_attr("href"):
            link["href"] = update_link(link["href"], template_path, save_path)

    # a links
    for a in html.find_all("a"):
        if a.has_attr("href"):
            link_href = a["href"]

            # if the link is an hpp file, lets link to the github link since we likely don't have it in our docs
            if link_href.find(config.GLM_MODULE_CONFIG["source_file_ext"]) > -1:
                a["href"] = config.GLM_MODULE_CONFIG["url_prefix"] + a.text
            else:
                a["href"] = update_link(a["href"], template_path, save_path)

    # script links
    for script in html.find_all("script"):
        if script.has_attr("src"):
            script["src"] = update_link(script["src"], template_path, save_path)

    # images
    for img in html.find_all("img"):
        if img.has_attr("src"):
            img["src"] = update_link(img["src"], template_path, save_path)

    # iframes
    for iframe in html.find_all("iframe"):
        if iframe.has_attr("src"):

            print "----"
            link_src = iframe["src"]
            print posixpath.isabs(link_src)
            
            if link_src.startswith('javascript') or link_src.startswith('http'):
                print "RETURN NOW BUDDY"
                return

            # on osx/unix
            if os.sep == "/":
                # if a relative link
                if not posixpath.isabs(link_src):
                    link_src = "/" + link_src
            print link_src
            

            # base dir
            src_base = src_path.split(PATHS["BASE_PATH"])[1].split(os.sep)[0]
            dest_base = save_path.split(PATHS["BASE_PATH"])[1].split(os.sep)[0]

            # get link of iframe source and replace in iframe
            new_link = update_link(link_src, template_path, save_path)
            iframe["src"] = new_link

            # define the paths of file to copy and where to copy to
            src_file = link_src
            dest_file = link_src.replace(src_base, dest_base)

            
            print iframe
            print src_file
            print dest_file
            print dest_base
            print "----"

            try:
                # copy file as long as the source and destination is not the same
                if SM(None, src_file, dest_file).ratio() < 1.0:
                    shutil.copy2(src_file, dest_file)
            except IOError as e:
                log("Cannot copy src_file because it doesn't exist: " + src_file, 2)
                log(e.strerror, 2)
                return
            except Exception as e:
                log("Cannot copy iframe over because of some other error", 2)
                log(str(e), 2)
                return


def update_link(link, in_path, out_path):
    """
    Update the given link to point to something relative to the new path
    :param link: The link to change
    :param in_path: the original path to the file that the link lives in
    :return:
    """

    if link.startswith("http") or link.startswith("javascript:") or link.startswith("#"):
        return link

    SEPARATOR = '/'
    in_path = in_path.replace('\\', SEPARATOR)
    out_path = out_path.replace('\\', SEPARATOR)
    link = link.replace('\\', SEPARATOR)
    base_path = PATHS["BASE_PATH"].replace('\\', SEPARATOR)

    # if a relative path, make it absolute
    if in_path.find(base_path) < 0:
        in_path = base_path + in_path
    
    # get absolute in path
    abs_link_path = update_link_abs(link, in_path)

    # convert to relative link in relation to the out path
    src_base = in_path.split(base_path)[1].split(SEPARATOR)[0]        # likely htmlsrc
    dest_base = out_path.split(base_path)[1].split(SEPARATOR)[0]      # htmlsrc or html

    abs_dest = posixpath.dirname(out_path).replace('\\', SEPARATOR)
    abs_link = abs_link_path.replace(src_base, dest_base)
    # if not posixpath.isabs(abs_link):
        # abs_link = "/" + abs_link

    rel_link_path = relative_url(abs_dest, abs_link)

    return rel_link_path


# =============================================================================================== File utils

def get_file_prefix(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]


def get_file_extension(file_path):
    return os.path.splitext(os.path.basename(file_path))[1]


def get_file_name(file_path):
    return os.path.basename(file_path)


def parse_xml(in_path):
    """
    Opens the xml file and turns it into an ETree
    :param in_path:
    :return:
    """

    tree = None
    try:
        with open(in_path, "rb") as xml_file:
            content = xml_file.read().decode("utf-8", errors="replace")
            new_content = content.encode("utf-8", errors="replace")
            parser = ET.XMLParser(encoding="utf-8")
            tree = ET.fromstring(new_content, parser)

    except:
        exc = sys.exc_info()[0]
        log("COULD NOT PARSE FILE: " + in_path, 2)
        log(exc, 2)
    return tree


def write_html(bs4, save_path):
    """
    Writes the html file to disk
    :param bs4:
    :param save_path:
    :return:
    """

    # prettify descriptions
    for markup in bs4.find_all("div", "description"):
        if type(markup) is Tag:
            pretty = BeautifulSoup(markup.prettify())
            if pretty is not None and markup is not None:
                markup.replaceWith(pretty)

    # convert entities in code blocks
    for c in bs4.find_all("code"):
        for child in c.children:
            # replaces with escaped code
            try:
                child_utf = unicode(child).encode("utf-8", errors="replace")
                child.replace_with(str(child_utf))
            except Exception as e:
                log("Writing HTML | " + str(e), 2)

    # enode bs4, decode, and then re-encode and write
    document = bs4.encode(formatter="html")
    document = codecs.decode(document, "utf-8", "xmlcharrefreplace")

    if not os.path.exists(os.path.dirname(save_path)):
        os.makedirs(os.path.dirname(save_path))
    with codecs.open(save_path, "w", "utf-8") as outFile:
        outFile.write(document)



# ============================================================================================== Dynamic Page Generation


def generate_dynamic_markup(ref_data):

    # find template if it exists

    ref_id = ref_data["id"]
    if ref_id == "glm":
        return_markup = generate_glm_reference()
    elif ref_id == "namespaces":
        return_markup = generate_namespace_data()
    elif ref_id == "classes":
        return_markup = generate_class_list_data()
    else:
        return_markup = "NOTHING FOUND"
        log("No rules for generating dynamic content for id'" + ref_id + "' was found", 1)

    # plug data into template (if it exists)
    template_path = os.path.join(PATHS["TEMPLATE_PATH"], ref_data["template"])
    markup = bs4utils.render_template(template_path, return_markup)
    return markup


def generate_glm_reference():

    glm_group_data = {
        "groups": []
    }

    # add group data to glm reference data object
    for group_name in g.symbolsMap.groups:
        group = g.symbolsMap.find_group(group_name)
        group_data = {}
        group_data["name"] = group.title
        group_data["path"] = group.path
        group_data["description"] = group.description

        subgroups = []
        if len(group.subgroups) > 0:
            for subgroup in group.subgroups:
                subgroup_data = {}
                subgroup_data["name"] = subgroup.title
                subgroup_data["path"] = subgroup.path
                subgroup_data["description"] = subgroup.description
                subgroups.append(subgroup_data)
            group_data["subgroups"] = subgroups
            glm_group_data["groups"].append(group_data)

    return glm_group_data


def generate_namespace_data():

    ns_data = {
        "namespaces": []
    }

    namespaces = g.symbolsMap.get_whitelisted_namespaces()
    for ns in namespaces:
        ns = {
            "link": ns.path,
            "label": ns.name
        }
        ns_data["namespaces"].append(ns)

    return ns_data


def generate_class_list_data():

    classlist_data = {
        "classes": []
    }

    classes = g.symbolsMap.get_ordered_class_list()
    for c in classes:
        class_data = {
            "link": c.path,
            "label": c.name
        }
        classlist_data["classes"].append(class_data)

    return classlist_data


def inject_html(src_content, dest_el, src_path, dest_path):
    """
    Append a chunk of html into a specific div
    :param src_content: The src html to be injected
    :param dest_el: The div to inject the src html into
    :param src_path: The path of the src file so that we can gix teh relative links
    :return:
    """

    if not dest_el:
        log("destination element does not exist", 1)

    update_links(src_content, src_path, src_path, dest_path)

    try:
        # copy source content into to bs4 instance so that we can copy over without messing up the source
        bs4 = BeautifulSoup(str(src_content).decode("UTF-8"))
        # copy all Tags over to dest element
        for content in bs4.body.contents:
            if type(content) is Tag:
                dest_el.append(content)
    except AttributeError as e:
        log("appending html content to element [ " + e.message + " ]", 2)


# ================================================================================================== Misc helper classes


class LinkData(object):

    def __init__(self, link=None, label=None, active=True):
        self.link = link
        self.label = label
        self.active = active


# ==================================================================================================

def find_compound_name(tree):
    for compound_def in tree.iter("compounddef"):
        for compound_name in compound_def.iter("compoundname"):
            return compound_name.text


def find_file_kind(tree):
    kind = tree.find(r"compounddef").attrib['kind']
    return kind


def find_member_anchor(member):
    """
    Parses out the anchor tag from a member
    """
    anchor_str = member.attrib["id"].split("_1")[-1]
    return anchor_str


def find_file_kind_explicit(tree):
    """
    Find a more specific file kind based on the name of the file.
    So instead of just class as the tag file specifies its kind as,
    it might also be a struct or interface.
    :param tree:
    :return: string of kind
    """
    obj_id = tree.find(r"compounddef").attrib['id']
    if obj_id.startswith("struct"):
        if obj_id.endswith("_t"):
            return "struct_template"
        else:
            return "struct"

    elif obj_id.startswith("interface"):
        return "interface"

    elif obj_id.startswith("namespace"):
        return "namespace"

    else:
        if obj_id.endswith("_t"):
            return "class_template"
        else:
            return "class"


def find_compound_name_stripped(tree):
    compound_name = find_compound_name(tree)
    name = strip_compound_name(compound_name)
    return name