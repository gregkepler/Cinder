import os

def get_parent_dir(directory):
    import os
    return os.path.dirname(directory)

# static path vars
BASE_PATH = get_parent_dir(os.path.dirname(os.path.realpath(__file__))) + os.sep
HTML_ROOT_DIR = 'html'
XML_SOURCE_PATH = BASE_PATH + 'xml' + os.sep
HTML_DEST_PATH = BASE_PATH + HTML_ROOT_DIR + os.sep
HTML_SOURCE_PATH = BASE_PATH + 'htmlsrc' + os.sep
TEMPLATE_PATH = BASE_PATH + 'htmlsrc' + os.sep + "_templates" + os.sep
PARENT_DIR = BASE_PATH.split(os.sep + 'docs')[0]
TAG_FILE_PATH = "doxygen" + os.sep + "cinder.tag"