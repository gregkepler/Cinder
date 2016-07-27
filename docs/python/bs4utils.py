import os
from bs4 import Comment, NavigableString, Tag, BeautifulSoup
# from utils import relative_url, path_join
import utils
import globals as g
from globals import PATHS
from pystache.renderer import Renderer, Loader

# convert docygen markup to html markup
tagDictionary = {
    "linebreak": "br",
    "emphasis": "em",
    "ref": "a",
    "ulink": "ulink",
    "computeroutput": "code",
    "includes": "span",
    "simplesect": "span",
    "para": "p"
}


def gen_anchor_tag(bs4, anchor_name):
    anchor = gen_tag(bs4, "a")
    anchor["name"] = anchor_name
    return anchor


def gen_tag(bs4, tag_type, classes=None, contents=None):
    """ Generates a new html element and optionally adds classes and content

    Args:
        bs4:        beautiful soup
        tagType:    html tag/element (p, a, em, etc)
        classes:    array of strings that you want as classes for the element
        contents:   any content that you want to populate your tag with, if known
    """

    new_tag = bs4.new_tag(tag_type)

    if classes:
        for c in classes:
            add_class_to_tag(new_tag, c)

    if contents:
        if type(contents) is list:
            for c in contents:
                new_tag.append(clone(c))
        else:
            new_tag.append(contents)

    return new_tag


def gen_link_tag(bs4, text, link, target = "_self"):
    link_tag = gen_tag(bs4, "a", [], text)
    define_link_tag(link_tag, {"href": link})
    link_tag["target"] = target
    return link_tag


def gen_rel_link_tag(bs4, text, link, src_dir, dest_dir):
    """
    Generates a link tag that was relative to the source directory, but should now be relative to the destination directory
    :param bs4: beautifulsoup instance
    :param text: text of link
    :param link: relative link
    :param src_dir: original source directory
    :param dest_dir: destination source directory
    :return: the link tag
    """

    # make sure they are dirs
    src_dir = os.path.dirname(src_dir) + os.sep
    dest_dir = os.path.dirname(dest_dir) + os.sep
    new_link = utils.relative_url(dest_dir, link)
    link_tag = gen_link_tag(bs4, text, new_link)
    return link_tag


def replace_element(bs4, element, replacement_tag):
    """
    Replaces an html element with another one, keeping the text contents.
    Use Case: Useful for replacing links with em tags or divs with spans
    :param bs4: Beautiful Soup instance doing the work
    :param element: element to change
    :param replacement_tag: new element type to change to
    :return:
    """
    if not element:
        return

    text_content = element.text
    replacement = gen_tag(bs4, replacement_tag, None, text_content)
    element.replace_with(replacement)


def get_body_content(bs4):
    return_str = ""
    for content in bs4.body.contents:
        content_utf = unicode(content).encode("utf-8", errors="replace")
        content_str = content_utf.decode("utf-8", errors="replace")
        if type(content) is Comment:
            return_str += "<!-- " + content_str + "-->"
        else:
            return_str += content_str
    return return_str


def markup_brief_description(bs4, tree, description_el=None):
    if description_el is None:
        description_el = gen_tag(bs4, "div", ["description", "content"])

    brief_desc = tree.findall(r'briefdescription/')
    if brief_desc is None:
        return
    else:
        for desc in brief_desc:
            iterate_markup(bs4, desc, description_el)

    return description_el


def markup_description(bs4, tree):
    description_el = gen_tag(bs4, "div", ["description", "content"])

    # mark up brief description first
    markup_brief_description(bs4, tree, description_el)

    # mark up detailed description next
    detailed_desc = tree.findall(r'detaileddescription/')

    if detailed_desc is not None:
        for desc in detailed_desc:
            iterate_markup(bs4, desc, description_el)

    return description_el


def add_class_to_tag(tag, class_name):
    tag["class"] = tag.get("class", []) + [class_name]


def iterate_markup(bs4, tree, parent):
    if tree is None:
        return

    current_tag = parent
    content = None

    # add content to tag as is ( no stripping of whitespace )
    if tree.text is not None:
        content = tree.text

    # append any new tags
    if tree.tag is not None:
        html_tag = replace_tag(bs4, tree, current_tag, content)
        # if tree parent == <p> && newTag == <pre>
        # add a new pre tag in and make that the current parent again
        current_tag = html_tag

    # iterate through children tags
    for child in list(tree):
        iterate_markup(bs4, child, current_tag)

    # tail is any extra text that isn't wrapped in another tag
    # that exists before the next tag
    if tree.tail is not None:
        parent.append(tree.tail)
        if tree.tail.endswith(";"):
            parent.append(gen_tag(bs4, "br"))

    return current_tag


def iter_class_base(class_def, hierarchy):
    """ Iterates the class to find all of their base classes
        and iterate through them
    Args:
        classDef: The instance of SymbolMap::Class Object whose base we are searching for
        hierachy: The current hierachy of classes to append to if we find another base
    """

    if class_def is None or hasattr(class_def, 'name') is False:
        return False

    base = class_def.base

    if base is None:
        return False
    else:
        new_tree = g.symbolsMap.find_class(base)
        # add to hierarchy if it continues
        if iter_class_base(new_tree, hierarchy) is not False:
            hierarchy.append(new_tree)


def gen_class_hierarchy(bs4, class_def):
    """ Generates the class hierarchy side bar, with each class linking
        out to its class file.
    Args:
        bs4: The current beautifulSoup html instance
        classDef: The instance of SymbolMap::Class Object that we are generating
            the hierachy for
    Returns:
        Empty if there is no base class
        Ul if there is hierarchy
    """

    if class_def is None:
        return

    # first item in the list will be the original class
    hierarchy = []

    # get the class' hierarchy
    iter_class_base(class_def, hierarchy)
    hierarchy.append(class_def)

    if len(hierarchy) == 1:
        return

    # create all of the markup
    ul = gen_tag(bs4, "ul")
    add_class_to_tag(ul, "inheritence")

    # go through the hierarchy and add a list item for each member
    # for index, base in enumerate(reversed(hierarchy)):
    for index, base in enumerate(hierarchy):
        li = gen_tag(bs4, "li")
        add_class_to_tag(li, "depth" + str(index + 1))

        # link out only if a base class, not the original class
        if index < len(hierarchy) - 1:
            a = gen_tag(bs4, "a", [], base.qualifiedName)
            define_link_tag(a, {'href': base.path})
            a = gen_link_tag(bs4, base.qualifiedName, utils.path_join(PATHS["HTML_DEST_PATH"], a["href"]))
            li.append(a)
        else:
            li.append(base.qualifiedName)
        ul.append(li)

    return ul

def replace_tag(bs4, tree, parent_tag, content):
    tag = tree.tag
    attrib = tree.attrib
    has_parent = False
    tag_name = None

    if parent_tag and parent_tag.parent:
        has_parent = True

    # change parentTag if necessary
    if tag == "codeline":
        parent_tag = parent_tag.code

    # find html tag based on tag
    if tag == "para":
        if has_parent and parent_tag.parent.dl:
            tag_name = "dd"
        else:
            tag_name = tagDictionary[tag]
    elif tag == "sp":
        if content is None:
            content = " "
        else:
            content.append(" ")

    # get tag equivalent
    if tag in tagDictionary:
        tag_name = tagDictionary[tag]
        new_tag = define_tag(bs4, tag_name, tree)
    else:
        # TODO: replace with nothing - no new tag
        tag_name = "span"
        new_tag = define_tag(bs4, tag_name, tree)
        add_class_to_tag(new_tag, tag)

    content_tag = new_tag

    # if simplesect, construct with some content
    if tag == "simplesect":
        see_tag = bs4.new_tag("dt")
        add_class_to_tag(see_tag, "section")

        # "see also" reference
        if attrib["kind"] == "see":
            add_class_to_tag(see_tag, "see")
            see_tag.string = "See Also"
        new_tag.append(see_tag)

    if tag == "programlisting":
        code_tag = bs4.new_tag("code")
        add_class_to_tag(code_tag, "language-cpp")
        new_tag.append(code_tag)
        content_tag = code_tag

    if tag == "computeroutput":
        if content:
            content = content.strip()

    if content is not None:
        content_tag.append(content)

    parent_tag.append(new_tag)
    return new_tag


def define_tag(bs4, tag_name, tree):
    """ Creates a new html element with the specified tag_name. "a" tags and "ulink" 
        tags are different since it generates a tags with links defined in the tree.

    Args:
        bs4: BeautifulSoup instance
        tag_name: What the new tag should be
        tree: original element tree which contains extra optional information
    """
    
    if tag_name == "a":
        new_tag = bs4.new_tag(tag_name)
        define_link_tag(new_tag, tree.attrib)
        # creates a new tag with a relative link using the data from the original tag
        # TODO: refactor define_tag and ren_link_tags. Should be able to create relative link on its own
        # new_tag = gen_rel_link_tag(bs4, "", new_tag["href"], TEMPLATE_PATH, DOXYGEN_HTML_PATH)
        new_tag = gen_link_tag(bs4, "", "../" + new_tag["href"])
    elif tag_name == "ulink":
        # ulinks are for external links
        new_tag = bs4.new_tag("a")
        new_tag = gen_link_tag(bs4, "", tree.attrib['url'], "_blank")
    else:
        new_tag = bs4.new_tag(tag_name)
    return new_tag


def define_link_tag(tag, attrib):
    ref_id = None
    href = None

    if "refid" in attrib:
        ref_id = attrib["refid"]
        href = ref_id + ".html"

    if "kindref" in attrib:
        kind = attrib["kindref"]

        if kind == "member":
            str_list = ref_id.rsplit("_1", 1)
            href = str_list[0] + ".html#" + str_list[1]

    if "linkid" in attrib:
        href = "../../include/cinder/" + attrib["linkid"]

    if "href" in attrib:
        href = attrib["href"]

    if "typedef" in attrib:
        data = attrib["typedef"]
        file_name = data.find("anchorfile").text
        anchor = data.find("anchor").text
        href = file_name + "#" + anchor

    if href is None:
        log("DEFINING LINK TAG: " + str(tag), 1)
    else:
        tag["href"] = href


# clone an element
# from: http://stackoverflow.com/questions/23057631/clone-element-with-beautifulsoup/23058678#23058678
def clone(el):
    if isinstance(el, NavigableString):
        return type(el)(el)

    tag_copy = Tag(None, el.builder, el.name, el.namespace, el.nsprefix)
    # work around bug where there is no builder set
    # https://bugs.launchpad.net/beautifulsoup/+bug/1307471
    tag_copy.attrs = dict(el.attrs)
    tag_copy.index = el.index
    for attr in ('can_be_empty_element', 'hidden'):
        setattr(tag_copy, attr, getattr(el, attr))
    for child in el.contents:
        tag_copy.append(clone(child))
    return tag_copy


def replace_code_chunks(bs4):
    """
    Looks though the html and replaces any code chunks that exist
    in a paragraph and splits them up so that we can use pre tags.
    :param bs4:
    :return:
    """

    # find all the code chunks
    code_chunks = bs4.find_all("div", "programlisting")
    code_chunks += bs4.find_all("span", "programlisting")

    for chunk in code_chunks:
        pre_tag = bs4.new_tag("pre")
        code_tag = bs4.new_tag("code")
        add_class_to_tag(code_tag, "language-cpp")

        # for each code line, add a line of that text to the new div
        codeline = chunk.find_all("div", "codeline")
        codeline += chunk.find_all("span", "codeline")

        if codeline:
            for line in codeline:
                line_text = ""
                for c in line.contents:
                    if type(c) is Tag:
                        line_text += c.text
                    else:
                        line_text += c
                code_tag.append(line_text + "\n")
            pre_tag.append(code_tag)

        # replace content in code chunks
        chunk.clear()
        replacement_span = gen_tag(bs4, "span")
        replacement_span.append(pre_tag)
        chunk.append(pre_tag)


def get_template(bs4, element_id):
    templates = bs4.find_all('template')
    template = None

    for t in templates:
        # [0] is a string before the enclosed div, so used [1] instead
        if t['id'] == element_id:
            template = clone(list(t.contents)[1])
        else:
            continue

    return template


def generate_namespace_nav():
    """
    Creates a div filled with a list of namespace links
    :param bs4: The Beautiful soup instance used for dom manipulation
    :return: a new div that contains the navigation tree
    """
    bs4 = BeautifulSoup()
    namespaces = g.symbolsMap.get_whitelisted_namespaces()

    # tree = gen_tag(bs4, "div")
    ul = gen_tag(bs4, "ul")
    # tree.append(ul)
    add_class_to_tag(ul, "css-treeview")
    ul["id"] = "namespace-nav"

    iterate_namespace(bs4, namespaces, ul, 0, "")
    return ul


def iterate_namespace(bs4, namespaces, tree, index, label):
    # Get namespace of previous child, unless first
    if index == 0:
        parent_ns = ""
    else:
        parent_ns = namespaces[index - 1].name

    count = index
    child_count = 0

    # iterate to find all children of parentNs
    for ns in namespaces[index:]:
        namespace = ns.name  # full namespace
        ns_parts = namespace.split("::")
        prefix = "::".join(ns_parts[:-1])  # parent namespace up to last ::

        name = "".join(ns_parts[-1])
        node_label = label + str(child_count)

        # check if derived from any parent
        parent_is_derived = has_ancestor(namespaces, namespace)

        # create a list item for the namespace
        ns_li = gen_tag(bs4, "li")
        ns_li["data-namespace"] = namespace

        # create link for each item
        a_tag = gen_link_tag(bs4, name, utils.path_join(PATHS["HTML_SOURCE_PATH"], ns.path))

        # is decendent of parent namespace
        if prefix == parent_ns:

            child_count += 1

            # append to parent
            tree.append(ns_li)

            # generate new nested ul in case there are children
            ns_ul = gen_tag(bs4, "ul")
            if count < len(namespaces):

                # if there are children, add to the parent ul
                if iterate_namespace(bs4, namespaces, ns_ul, count + 1, node_label) > 0:
                    # add input
                    input_el = gen_tag(bs4, "input")
                    input_el["type"] = "checkbox"
                    input_el["id"] = "item-" + "-".join(list(node_label))

                    # root is expanded by default
                    if index == 0:
                        input_el.attrs["checked"] = "true"

                    label_tag = gen_tag(bs4, "label")
                    label_tag["for"] = "item-" + "-".join(list(node_label))
                    label_tag.append(a_tag)

                    ns_li.insert(0, input_el)
                    ns_li.append(label_tag)
                    ns_li.append(ns_ul)
                else:
                    ns_li.append(a_tag)

        else:
            # has no direct descendent on the parent, so add it independently
            if parent_is_derived is False and index is 0:
                child_count += 1
                indie_li = gen_tag(bs4, "li")
                # indieLi.append( prefix )

                # TODO: refactor and simplify some of this stuff
                input_el = gen_tag(bs4, "input")
                input_el["type"] = "checkbox"
                input_el["id"] = "item-" + "-".join(list(node_label))
                indie_li.insert(0, input_el)

                label_tag = gen_tag(bs4, "label")
                label_tag["for"] = "item-" + "-".join(list(node_label))
                label_tag.append(prefix)
                indie_li.append(label_tag)

                indie_ul = gen_tag(bs4, "ul")
                indie_li.append(indie_ul)
                indie_ul.append(ns_li)
                ns_li.append(a_tag)

                tree.append(indie_li)

        count += 1

    return child_count



def has_ancestor(namespaces, compare_namespace):
    compare_prefix = "::".join(compare_namespace.split("::")[0])
    # hasAncestor = False
    for ns in namespaces:
        namespace = ns.name
        prefix = "::".join(namespace.split("::")[0])
        if prefix == compare_prefix and compare_namespace != namespace:
            return True

    return False


def generate_bs4(file_path):

    # tree = None
    try:
        with open(file_path, "rb") as html_file:
            content = html_file.read().decode("utf-8", errors="replace")
            new_content = content.encode("utf-8", errors="replace")

        # wrap in body tag if none exists
        if new_content.find("<body") < 0:
            new_content = "<body>" + new_content + "</body>"
            log("No body tag found in file: " + file_path)

        bs4 = BeautifulSoup(new_content)
        return bs4

    except Exception as e:
        log(e.message, 2)
        return None


def generate_bs4_from_string(string):

    # make sure it's a unicode object
    if type(string) != unicode:
        output_string = string.decode("utf-8", errors="replace")
    else:
        output_string = string

    # wrap in body tag if none exists
    if string.find("<body") < 0:
        output_string = "<body>" + output_string + "</body>"

    bs4 = BeautifulSoup(output_string)
    return bs4


def render_template(path, content):
    """
    Generates a BeautifulSoup instance from the template and injects content
    :param path:
    :param content:
    :return:
    """
    # try:
    # renderer = Renderer(file_encoding="utf-8", string_encoding="utf-8", decode_errors="xmlcharrefreplace")
    # renderer.search_dirs.append(PATHS["TEMPLATE_PATH"])
    # output = renderer.render_path(path, content)


    # print content
    # print path
    # step 1: render content in template
    content_renderer = Renderer(file_encoding="utf-8", string_encoding="utf-8", decode_errors="xmlcharrefreplace")
    content_renderer.search_dirs.append(PATHS["TEMPLATE_PATH"])
    output = content_renderer.render_path(path, content)

    # step 2: place rendered content into main template
    # - should have the following custom partials:
    #   - page title (define in object for page templates)
    #   - page content (rendered page content)
    #   - any other common partials that may lie outside the basic content area

    # loader = Loader()
    # template = loader.read("title")
    # title_partial = loader.load_name(os.path.join(CLASS_TEMPLATE_DIR, "title"))

    # except Exception as exc:
    #     print "\t**--------------------------------"
    #     print "\t** Warning: cannot render template"
    #     print "\t**--------------------------------"
    #     print exc
    #     print exc.message
    #     print(traceback.format_exc())
    #     exc_type, exc_obj, exc_tb = sys.exc_info()
    #     fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    #     print(exc_type, fname, exc_tb.tb_lineno)
    #
    #     if config.BREAK_ON_STOP_ERRORS:
    #         quit()
    #     else:
    #         return

    bs4 = generate_bs4_from_string(output)
    return bs4