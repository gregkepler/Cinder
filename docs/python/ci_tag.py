import utils
import bs4utils
from utils import log
from symbol_map import SymbolMap
import globals as g
from globals import PATHS

# ===================================================================================================== CI Tag Functions


def process_ci_tag(bs4, tag, in_path, out_path):
    """
    Depending on the attributes of the ci tag, do something different
    :param bs4: The current beautiful soup instance
    :param tag: The ci tag to process
    :param in_path: The path to the current processed html file
    :param out_path: The save path to the prcessing html file
    :return:
    """
    if tag.has_attr("seealso"):
        process_ci_seealso_tag(bs4, tag, out_path)

    elif tag.has_attr("prefix"):
        process_ci_prefix_tag(bs4, tag, in_path)

    # elif tag.has_attr("source"):
    #     process_ci_source_tag(bs4, tag)

    else:
        replace_ci_tag(bs4, tag, in_path, out_path)


def replace_ci_tag(bs4, link, in_path, out_path):
    ref_obj = find_ci_tag_ref(link)

    if ref_obj:
        ref_location = utils.path_join(PATHS["HTML_DEST_PATH"], ref_obj.path)
        new_link = bs4utils.gen_rel_link_tag(bs4, link.contents, ref_location, out_path)

        # transfer tag classes to new tag
        tag_classes = link["class"] if link.has_attr("class") else None
        if tag_classes:
            for c in tag_classes:
                bs4utils.add_class_to_tag(new_link, c)

        bs4utils.add_class_to_tag(new_link, "ci")
        link.replace_with(new_link)
    else:
        log("Could not find replacement tag for ci tag: " + str(link), 1)


def process_ci_seealso_tag(bs4, tag, out_path):
    """
    Processes ci tag that is of 'seealso' type
    :param bs4: The active beautiful soup instance
    :param tag: the ci tag to find a reference for
    :param out_path: the file path
    :return: None
    """
    ref_obj = find_ci_tag_ref(tag)

    # get label attribute value if there is one
    if tag.has_attr("label"):
        label = tag["label"]
    # otherwise use the name of the file as the label
    else:
        label = utils.get_file_name(out_path)

    # link_tag = gen_link_tag(bs4, label, out_path)
    link_data = utils.LinkData(out_path.replace("\\", "/"), label)

    # if type(ref_obj) is SymbolMap.Class or type(ref_obj) is SymbolMap.Typedef:
    if type(ref_obj) is SymbolMap.Class:
        ref_obj.add_related_link(link_data)

    elif type(ref_obj) is SymbolMap.Namespace:
        # find all classes with that namespace and add guide to every one
        for class_obj in g.symbolsMap.find_classes_in_namespace(ref_obj.name):
            class_obj.add_related_link(link_data)
    else:
        log("Could not find seealso reference for " + str(tag), 1)


def process_ci_prefix_tag(bs4, tag, in_path):
    """
    Finds the referenced tag's object if existent and adds the path to the prefix file to the class to be parsed later
    :param tag: The ci tag with a defined prefix attribute
    :param in_path: The path to the refix content
    :return:
    """
    in_path = in_path.replace('\\', '/')
    in_dir = utils.get_path_dir(in_path)

    obj_ref = find_ci_tag_ref(tag)
    if obj_ref and type(obj_ref) is SymbolMap.Class:

        # get tag content
        prefix_content = ""
        for c in tag.contents:
            content = c.encode("utf-8", errors="replace")
            prefix_content += content

        # generate bs4 from content and update links as reltive from the template path
        # could alternatively set the absolute paths of content, which would then be turned into rel paths later
        new_bs4 = bs4utils.generate_bs4_from_string(prefix_content)
        utils.update_links(new_bs4, in_dir, in_path, PATHS["TEMPLATE_PATH"])

        # get updated body content and assign as prefix_content
        prefix_content = ""
        for c in new_bs4.body:
            content = c.encode("utf-8", errors="replace")
            prefix_content += content

        obj_ref.define_prefix(prefix_content)


# TODO: add ability to replace ci tag with link to github source file
# def process_ci_source_tag(bs4, tag):
#     """
#     Replace the ci tag with a link to a source file on github
#     :param tag: the tag to find a link for
#     :return:
#     """
#     link_title = "LINK TITLE"
#     # link_url =
#     link_tag = gen_link_tag(bs4, link_title)

def find_ci_tag_ref(link):
    # get string to search against
    searchstring = ""
    if len(link.contents):
        searchstring = link.contents[0]

    if link.get('dox') is not None:
        searchstring = link.get('dox')

    ref_obj = None
    
    is_function = searchstring.find("(") > -1 or link.get('kind') == 'function'
    if is_function:
        arg_string = searchstring[searchstring.find("("):]
        if len(arg_string) == 0:
            arg_string = "()"

    try:
        # find function link
        if is_function:
            fn_obj = g.symbolsMap.find_function(searchstring, arg_string)
            if fn_obj is not None:
                ref_obj = fn_obj

        # find enum link
        elif link.get('kind') == 'enum':
            enum_obj = g.symbolsMap.find_enum(searchstring)
            if enum_obj is not None:
                ref_obj = enum_obj

        # find class link
        else:
            existing_class = g.symbolsMap.find_class(searchstring)
            if existing_class is not None:
                ref_obj = existing_class

            else:
                count = 0
                # try a bunch of other things before giving up
                while (ref_obj is None) and count < 3:
                    if count == 0:
                        ref_obj = g.symbolsMap.find_namespace(searchstring)
                    elif count == 1:
                        ref_obj = g.symbolsMap.find_function(searchstring)
                    elif count == 2:
                        ref_obj = g.symbolsMap.find_enum(searchstring)
                    count += 1

    except Exception as e:
        log("problem finding ci tag", 1)
        log(e.message, 1)
        return None

    return ref_obj

