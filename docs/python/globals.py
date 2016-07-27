import os
from datetime import datetime
from search_index import SearchIndex

def get_parent_dir(directory):
    import os
    return os.path.dirname(directory)

# static path vars
BASE_PATH = get_parent_dir(os.path.dirname(os.path.realpath(__file__))) + os.sep
HTML_ROOT_DIR = 'html'
PATHS = {
    'BASE_PATH': BASE_PATH,
    'HTML_ROOT_DIR': HTML_ROOT_DIR,
    'XML_SOURCE_PATH': BASE_PATH + 'xml' + os.sep,
    'HTML_DEST_PATH': BASE_PATH + HTML_ROOT_DIR + os.sep,
    'HTML_SOURCE_PATH': BASE_PATH + 'htmlsrc' + os.sep,
    'TEMPLATE_PATH': BASE_PATH + 'htmlsrc' + os.sep + "_templates" + os.sep,
    'PARENT_DIR': BASE_PATH.split(os.sep + 'docs')[0],
    'TAG_FILE_PATH': "doxygen" + os.sep + "cinder.tag"
}

# BASE_PATH = get_parent_dir(os.path.dirname(os.path.realpath(__file__))) + os.sep
# HTML_ROOT_DIR = 'html'
# XML_SOURCE_PATH = BASE_PATH + 'xml' + os.sep
# HTML_DEST_PATH = BASE_PATH + HTML_ROOT_DIR + os.sep
# HTML_SOURCE_PATH = BASE_PATH + 'htmlsrc' + os.sep
# TEMPLATE_PATH = BASE_PATH + 'htmlsrc' + os.sep + "_templates" + os.sep
# PARENT_DIR = BASE_PATH.split(os.sep + 'docs')[0]
# TAG_FILE_PATH = "doxygen" + os.sep + "cinder.tag"

# various config settings
class Config(object):
    def __init__(self):
        # break on errors that would prevent the file from being generated
        self.BREAK_ON_STOP_ERRORS = True
        # whitelisted namespaces to generate pages for
        self.NAMESPACE_WHITELIST = [
            {
                "name": "cinder"
            },
            {
                "name": "glm",
                "structure_whitelist":
                [
                    {
                        "name": "typedefs",
                        "prefix_blacklist": ["lowp", "mediump", "highp"]
                    }
                ]
            }
        ]
        # blacklisted namespaces to generate pages for
        self.NAMESPACE_BLACKLIST = ["cinder::signals::detail", "cinder::audio::dsp::ooura", "cinder::detail", "glm::detail", "glm::gtc", "glm::gtx", "glm::io"]
        # blacklisted class strings - any class containing these strings will be skipped
        self.CLASS_LIST_BLACKLIST = ["glm", "@"]
        # cinder github repo path
        self.GITHUB_PATH = "http://github.com/cinder/Cinder/tree/master"
        # file that contains cinder meta data
        self.PROJECT_META_FILE = os.path.join(PATHS["XML_SOURCE_PATH"], "_cinder_8h.xml")

        # directory for the class template mustache file
        self.CLASS_TEMPLATE = os.path.join(PATHS["TEMPLATE_PATH"], "page-class-template.mustache")
        # directory for the namespace template mustache file
        self.NAMESPACE_TEMPLATE = os.path.join(PATHS["TEMPLATE_PATH"], "page-namespace-template.mustache")
        # directory for the namespace template mustache file
        self.GROUP_TEMPLATE = os.path.join(PATHS["TEMPLATE_PATH"], "page-group-template.mustache")
        # default html template mustache file
        self.HTML_TEMPLATE = os.path.join(PATHS["TEMPLATE_PATH"], "page-default-template.mustache")
        # guide html template mustache file
        self.GUIDE_TEMPLATE = os.path.join(PATHS["TEMPLATE_PATH"], "page-guide-template.mustache")
        # reference html template mustache file
        self.REFERENCE_TEMPLATE = os.path.join(PATHS["TEMPLATE_PATH"], "page-reference-template.mustache")
        # home page template mustache file
        self.HOME_TEMPLATE = os.path.join(PATHS["TEMPLATE_PATH"], "page-home-template.mustache")

        # file prefixes that indicate that the file should be parsed with the class template
        self.CLASS_FILE_PREFIXES = ["class", "struct", "interface"]
        # file prefixes that indicate that the file should be parsed with the namespace template
        self.NAMESPACE_FILE_PREFIXES = ["namespace"]
        # file prefixes that indicate that the file should be parsed with the group template
        self.GROUP_FILE_PREFIXES = ["group"]

        # configuration properties for different kinds of pages whose content is mostly dynamic from cinder.tag file
        self.DYNAMIC_PAGES_CONFIG = [
            # namespace list page
            {
                "id": "namespaces",
                "reference_html": "namespaces.html",
                "element_id": "namespace-content",
                "template": "namespace-list.mustache",
                "section": "namespaces",
                "searchable": False
            },
            # class list page
            {
                "id": "classes",
                "reference_html": "classes.html",
                "element_id": "classes-content",
                "template": "class-list.mustache",
                "section": "classes",
                "searchable": False
            },
            # glm reference page
            {
                "id": "glm",
                "reference_html": "reference/glm.html",
                "element_id": "glm-reference",
                "template": "glm-reference.mustache",
                "section": "reference",
                "searchable": True
            }
        ]

        # config for parsing glm group. In the future, we will standardize and externalize this so that we can
        # include and document additional modules
        self.GLM_MODULE_CONFIG = {
            "namespace": "glm",
            "url_prefix": "https://github.com/g-truc/glm/tree/0.9.6.3/",
            "group_keys": ["glm", "gtc", "gtx", "group__core"],
            "source_file_ext": "hpp"
        }

    def is_namespace_whitelisted(self, ns_str):
        if any([ns_str.startswith(prefix["name"]) for prefix in self.NAMESPACE_WHITELIST]):
            return True
        return None

    def is_namespace_blacklisted(self, ns_str):
        if any([ns_str.startswith(prefix) for prefix in self.NAMESPACE_BLACKLIST]):
            return True
        return False

    def get_ns_config(self, ns_str):
        for ns in self.NAMESPACE_WHITELIST:
            if ns["name"] == ns_str:
                return ns
        return None

    def get_section_config(self, sections, section_name):
        if sections:
            for sections in sections:
                if sections["name"] == section_name:
                    return sections
                return None
        return None

    def is_section_whitelisted(self, sections, section_name):
        '''
        Is the section of the page whitelisted
        :param sections: list page section configs
        :param section_name: name to check agains
        :return:
        '''
        if sections:
            for section in sections:
                if section["name"] == section_name:
                    whitelisted = True
                    break
                whitelisted = False
        else:
            whitelisted = True
        return whitelisted


# various state vars
class State(object):
    def __init__(self):
        self.html_files = []
        self.processed_html_files = False

    def add_html_file(self, file):
        self.html_files.append(file)

# globals
symbolsMap = None
g_tag_xml = None
search_index = SearchIndex()
config = Config()
state = State()
args = None
namespace_nav = None

# TODO: These should be dynamic via doxygen generated data. perhaps from _cinder_8h.xml
meta = {
    "cinder_version": "",
    "doxy_version": "",
    "creation_date": str(datetime.today().date()),
    "docs_root": ""
}
# logger = None