import os
import json
from file_types import HtmlFileData
import globals as g
from globals import PATHS, config
from bs4utils import *
from utils import log, GuideConfig
from ci_tag import process_ci_tag


def process_html_file(in_path, out_path):
    """ Parses an html file.
    - Adds template around the html
    - Copy original css and js links into new hmtl
    - Save html in destination dir
    """
#    log_progress('Processing file: ' + str(in_path))
    print 'Processing file: ' + str(in_path)
    # relative path in relation to the in_path (htmlsrc/)
    local_rel_path = os.path.relpath(in_path, PATHS["HTML_SOURCE_PATH"])
    # directory name of the path
    in_dir = os.path.dirname(in_path)
    # file name
    in_file_name = os.path.basename(in_path)

    # skip if it starts with "_", which means that it's not a first class citizen file and is supplemental
    if in_file_name.startswith("_"):
        return

    # get common data for the file
    file_data = HtmlFileData(in_path)

    # searchable by default
    is_searchable = True
    # tags for search engine
    search_tags = []

    # selected section of the website
    section = ""

    # parse guide config (if present in current directory)
    # this determines which function is used to generate dynamic page, which template to use, etc
    config_data = parse_config(in_dir, in_file_name)
    if config_data:
        # add search tags
        for k in config_data.keywords:
            search_tags.append(k)

        # plug in subnav data
        file_data.pagenav = config_data.pagenav

    # get correct template for the type of file
    template = config.HTML_TEMPLATE
    body_class = "default"
    if in_path.find("htmlsrc" + os.sep + "index.html") > -1:
        template = config.HOME_TEMPLATE
        is_searchable = False
        body_class = "section_home"
        section = "home"
    elif in_path.find("reference"+os.sep) > -1:
        template = config.REFERENCE_TEMPLATE
        body_class = "reference"
        section = "reference"
    elif in_path.find("guides"+os.sep) > -1:
        template = config.GUIDE_TEMPLATE
        body_class = "guide"
        section = "guides"

    # fill content ----------------------------------------

    # get source file body content
    orig_html = generate_bs4(in_path)

    # extract original scripts to append later
    orig_scripts = []
    for x in orig_html.findAll("script"):
        orig_scripts.append(x.extract())

    orig_links = []

    # get title
    if orig_html.head:
        if orig_html.head.title:
            file_data.title = orig_html.head.title.text

        for x in orig_html.findAll('link', rel="stylesheet"):
            orig_links.append(x.extract())

    # if there is a specific page that needs some special dynamic content, this is where we do it
    insert_div_id = ""
    dynamic_div = gen_tag(orig_html, "body")
    for data in config.DYNAMIC_PAGES_CONFIG:
        if "reference_html" in data and data["reference_html"] == local_rel_path:
            is_searchable = bool(data["searchable"])
            markup = utils.generate_dynamic_markup(data)
            for content in markup.body.contents:
                dynamic_div.append(content)
            insert_div_id = data["element_id"]

            if "section" in data:
                section = data["section"]

    # inject dynamic content into orig_html
    if insert_div_id:
        insert_el = orig_html.find(id=insert_div_id)
        utils.inject_html(dynamic_div, insert_el, in_path, out_path)

    # get body content out of bs4 and plug into file_data
    body_content = get_body_content(orig_html)
    file_data.html_content = body_content
    file_content = file_data.get_content()

    # render file template
    bs4 = render_template(template, file_content)
    utils.update_links_abs(bs4, os.path.dirname(in_path))
    content_dict = {'page_title': file_content["title"], 'main_content': get_body_content(bs4), 'body_class': body_class, str("section_" + section): "true"}
    # append file meta
    content_dict.update(g.meta.copy())

    # plug everything into the master template
    bs4 = render_template(os.path.join(PATHS["TEMPLATE_PATH"], "master-template.mustache"), content_dict)
    # make sure all links are absolute
    utils.update_links_abs(bs4, PATHS["TEMPLATE_PATH"])
    # now all links shoul be relative to out path
    utils.update_links(bs4, PATHS["TEMPLATE_PATH"], in_path, out_path)

    if bs4 is None:
        log("Error generating file, so skipping: " + in_path, 2)
        return

    # get list of all the css and js links in the new bs4
    link_list = bs4.head.find_all("link")
    script_list = bs4.body.find_all("script")

    # copy any css paths that may be in the original html and paste into new file
    for link in orig_links:
        # do not add duplicates
        if any(link_item["href"] == link["href"] for link_item in link_list):
            continue

        if bs4.head:
            bs4.head.append(link)

    # append original scripts to the end
    for script in orig_scripts:
        # do not add duplicates
        if script.has_attr("src") and any(script_item.has_attr("src") and script_item["src"] == script["src"] for script_item in script_list):
            continue
        if bs4.body:
            bs4.body.append(script)

    if orig_html.head:
        if bs4.head:
            for d in orig_html.head.find_all("ci"):
                bs4.head.append(d)

        # add ci seealso tags from config to bs4 head if it's the first in a group
        if config_data and config_data.order == 0:
            seealso_label = config_data.see_also_label
            for tag in config_data.see_also_tags:

                ci_tag = gen_tag(bs4, "ci")
                ci_tag.attrs["seealso"] = ""
                ci_tag.attrs["label"] = seealso_label
                ci_tag.attrs["dox"] = tag

                bs4.head.append(ci_tag)

        # add tags from the meta keywords tag
        for meta_tag in orig_html.head.findAll(attrs={"name": "keywords"}):
            for keyword in meta_tag['content'].split(','):
                search_tags.append(keyword.encode('utf-8').strip())

        # look for any meta 'group' tags to tell us that it's part of a grpup that will need nav
        for meta_tag in orig_html.head.findAll(attrs={"name": "group"}):
            if meta_tag['content']:
                file_data.group = meta_tag['content']

    # link up all ci tags
    for tag in bs4.find_all('ci'):
        process_ci_tag(bs4, tag, in_path, out_path)

    if in_path.find("_docs/") < 0:
        if is_searchable:
            link_path = gen_rel_link_tag(bs4, "", out_path, PATHS["HTML_SOURCE_PATH"], PATHS["HTML_DEST_PATH"])["href"]
            g.search_index.add(bs4, link_path, file_data.kind_explicit, search_tags)

        g.state.add_html_file(file_data)
        file_data.path = out_path
        utils.write_html(bs4, out_path)


def parse_config(path, file_name):
    # if "config.json" exists in path directory
    config_path = os.path.join(path, "config.json")
    if os.path.exists(config_path):
        # load and turn into GuideConfig object
        with open(config_path) as data_file:
            try:
                config_data = json.load(data_file)
                guide_config = GuideConfig(config_data, path, file_name)
            except Exception as e:
                log(str(e), 2)
                raise
        return guide_config
    else:
        return None