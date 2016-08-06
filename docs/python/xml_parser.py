import os
from bs4 import BeautifulSoup
from file_types import ClassFileData, NamespaceFileData, GroupFileData
import utils
from utils import log, log_progress, LinkData
import bs4utils
import globals as g
from globals import PATHS, config
import ci_tag


def process_xml_file_definition(in_path, out_path, file_type):
    """
    Process an xml file definition, such as a class, namespace, or group
    :param in_path: xml file location
    :param out_path: final html file location
    :param file_type: "class", "namespace", or "group"
    :return:
    """

    # we don't like files that start with '_'
    if os.path.basename(in_path).startswith("_"):
        return

    # define the tree that contains all the data we need to populate this page
    tree = utils.parse_xml(in_path)

    if tree is None:
        return

    # Determine type of file and generate content --------------------------------------------------

    if file_type == "class":
        if any(in_path.find(blacklisted) > -1 for blacklisted in config.CLASS_LIST_BLACKLIST):
            log("Skipping file | Class " + in_path + " blacklisted", 0)
            return

        html_template = config.CLASS_TEMPLATE
        file_data = fill_class_content(tree, in_path)
        file_data.section = "classes"
        file_data.body_class = "classes"

    elif file_type == "namespace":
        html_template = config.NAMESPACE_TEMPLATE
        file_data = fill_namespace_content(tree, in_path)

        if not file_data:
            return

        file_data.section = "namespaces"
        file_data.body_class = "namespaces"

    elif file_type == "module":
        html_template = config.GROUP_TEMPLATE
        file_data = fill_group_content(tree, in_path, config.GLM_MODULE_CONFIG)
        file_data.section = "reference"
        file_data.body_class = "reference"
    else:
        log("Skipping " + in_path, 1)
        return

    log_progress('Processing file: ' + str(in_path))

    # Generate the html file from the template and inject content ----------------------------------
    bs4 = render_file(file_data, html_template)

    # Clean up and write the file
    finalize_file(bs4, file_data, out_path)


def parse_namespaces(tree, sections):
    namespaces = []
    if config.is_section_whitelisted(sections, "namespaces"):
        for member in tree.findall(r"compounddef/innernamespace"):
            link = utils.path_join(PATHS["HTML_DEST_PATH"], member.attrib["refid"] + ".html")
            link_data = LinkData(link, member.text)
            namespaces.append(link_data)
    return namespaces


def parse_classes(tree, sections):
    classes = []
    if config.is_section_whitelisted(sections, "classes"):
        for member in tree.findall(r"compounddef/innerclass[@prot='public']"):
            link = member.attrib["refid"] + ".html"
            rel_link = utils.path_join(PATHS["HTML_DEST_PATH"], link)
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

            typedef_obj = utils.parse_member_definition(bs4, member)
            typedefs.append(typedef_obj)
    return typedefs


def parse_enums(bs4, tree, sections):
    enums = []
    if config.is_section_whitelisted(sections, "enums"):
        for member in tree.findall(r"compounddef/sectiondef/[@kind='enum']/memberdef/[@kind='enum']"):
            member_obj = utils.parse_enum(bs4, member)
            enums.append(member_obj)
    return enums


def parse_functions(bs4, tree, sections):
    fns = []
    if config.is_section_whitelisted(sections, "functions"):
        for member in tree.findall(r"compounddef/sectiondef/[@kind='func']/memberdef/[@kind='function']"):
            function_obj = utils.parse_member_definition(bs4, member)
            fns.append(function_obj)
    return fns


def parse_free_functions(bs4, tree, sections):
    free_fns = []
    if config.is_section_whitelisted(sections, "free_functions"):
        for member in tree.findall(r"compounddef/sectiondef/[@kind='user-defined']/memberdef/[@kind='function']"):
            function_obj = utils.parse_member_definition(bs4, member)
            free_fns.append(function_obj)
    return free_fns


def parse_vars(bs4, tree, sections):
    variables = []
    if config.is_section_whitelisted(sections, "variables"):
        for member in tree.findall(r"compounddef/sectiondef/[@kind='var']/memberdef/[@kind='variable']"):
            var_obj = utils.parse_member_definition(bs4, member)
            initializer = member.find('initializer').text if member.find('initializer') is not None else None
            var_obj["definition"]["args"] = initializer
            variables.append(var_obj)
    return variables


def fill_class_content(tree, in_path):
    """
    Populates the class content object with data
    :param tree:
    :return:
    """

    bs4 = BeautifulSoup()
    file_data = ClassFileData(tree, in_path)

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
    description = bs4utils.markup_description(bs4, tree.find(r'compounddef'))
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
        class_typedefs = utils.find_typedefs_of(class_name, ns_obj.typedefs)
        if file_def is not None:
            for t in class_typedefs:
                link_data = LinkData()
                link_data.label = t.name
                link_path = utils.path_join(PATHS["HTML_DEST_PATH"], t.path)
                link_data.link = link_path
                typedefs.append(link_data)
    file_data.typedefs = typedefs

    # class hierarchy ----------------------------------- #
    if class_def:
        class_hierarchy = bs4utils.gen_class_hierarchy(bs4, class_def)
        file_data.class_hierarchy = str(class_hierarchy) if class_hierarchy else None

    # class list ---------------------------------------- #
    classes = []
    for classDef in tree.findall(r"compounddef/innerclass[@prot='public']"):
        link_data = LinkData()
        link_data.label = utils.strip_compound_name(classDef.text)
        link_data.link = utils.path_join(PATHS["HTML_DEST_PATH"], classDef.attrib["refid"] + ".html")
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
        member_obj = utils.parse_enum(bs4, e)
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

        function_obj = utils.parse_function(bs4, memberFn, class_name)
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
        function_obj = utils.parse_function(bs4, member, class_name)
        protected_functions.append(function_obj)
    file_data.protected_functions = protected_functions

    # protected attributes ------------------------------ #
    protected_attrs = []
    for v in tree.findall(r'compounddef/sectiondef/memberdef[@kind="variable"][@prot="protected"]'):
        member_obj = utils.parse_member_definition(bs4, v)
        protected_attrs.append(member_obj)
    file_data.protected_attrs = protected_attrs

    # friends ------------------------------------------- #
    friends = []
    for member in tree.findall(r'compounddef/sectiondef/memberdef[@kind="friend"]'):
        member_obj = utils.parse_member_definition(bs4, member)

        # replace name with link to class
        friend_class = g.symbolsMap.find_class(member_obj["name"])

        # link up friend, if class exists
        if friend_class:
            friend_link = bs4utils.gen_rel_link_tag(bs4, friend_class.name, friend_class.path, PATHS["TEMPLATE_PATH"], PATHS["HTML_DEST_PATH"])
            member_obj["definition"]["name"] = str(friend_link)
        friends.append(member_obj)
    file_data.friends = friends

    if class_def:
        file_data.search_tags = class_def.tags

    return file_data


def fill_namespace_content(tree, in_path):

    bs4 = BeautifulSoup()

    if tree is None:
        return

    # get common data for the file
    file_data = NamespaceFileData(tree, in_path)
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


def fill_group_content(tree, in_path, module_config):
    bs4 = BeautifulSoup()
    file_data = GroupFileData(tree, in_path, module_config)

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
    description = bs4utils.markup_description(bs4, tree.find(r'compounddef'))
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
        typedef_obj = utils.parse_member_definition(bs4, member)
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
    memberFns = tree.findall(r'compounddef/sectiondef/memberdef[@kind="function"][@prot="public"]')
    for memberFn in memberFns:

        function_obj = utils.parse_function(bs4, memberFn, group_name)
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


def render_file(file_data, template):
    file_content = file_data.get_content()
    bs4 = bs4utils.render_template(template, file_content)
    content_dict = {
        "page_title": file_content["title"],
        "main_content": bs4utils.get_body_content(bs4),
        "body_class": file_data.body_class,
        "section_namespace": "cinder",
        str("section_" + file_data.section): "true"}
    # append file meta
    content_dict.update(g.meta.copy())

    # render within main template
    bs4 = bs4utils.render_template(os.path.join(PATHS["TEMPLATE_PATH"], "master-template.mustache"),
                                   content_dict)
    # make sure all links are absolute
    utils.update_links_abs(bs4, PATHS["TEMPLATE_PATH"])

    if not bs4:
        log("Skipping class due to something nasty. Bother Greg and try again some other time. "
            "Error rendering: " + file_data.in_path, 2)
        return None

    return bs4


def finalize_file(bs4, file_data, out_path):
    """
    Does any finalization that a file may need including replacing ci tags,
    adding the file to the search index, and writing the file.
    Args:
        bs4: the Beautiful Soup object containing all of the final content
        file_data: The data object that has config stuff

    Returns:

    """
    # update links in the template
    utils.update_links(bs4, PATHS["TEMPLATE_PATH"] + "htmlContentTemplate.html",
                       PATHS["TEMPLATE_PATH"], out_path)

    # replace any code chunks with <pre> tags, which is not possible on initial creation
    bs4utils.replace_code_chunks(bs4)

    # link up all ci tags
    for tag in bs4.find_all('ci'):
        ci_tag.process_ci_tag(bs4, tag, file_data.in_path, out_path)

    # add to search index
    link_path = bs4utils.gen_rel_link_tag(bs4, "", out_path, PATHS["HTML_SOURCE_PATH"],
                                          PATHS["HTML_DEST_PATH"])["href"]
    g.search_index.add(bs4, link_path, file_data.kind, file_data.search_tags)

    # deactivate invalid relative links
    for link in bs4.find_all("a"):
        if link.has_attr("href") and link["href"].startswith("_"):
            # replace <a> with <span>
            dead_tag = bs4utils.gen_tag(bs4, "span", None, link.string)
            link.replace_with(dead_tag)

    # write the file
    utils.write_html(bs4, out_path)