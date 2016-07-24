import os
from bs4 import Comment, NavigableString, Tag
from utils import relative_url

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
    new_link = relative_url(dest_dir, link)
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