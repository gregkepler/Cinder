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
import xml.etree.ElementTree as ET
import os
import shutil
import stat
import argparse

# Third party in libs folder
sys.path.append("libs/")
sys.path.append("python/")

import utils as utils
# from utils import strip_compound_name, parse_xml, log, log_progress, path_join, 
from utils import log, log_progress, LinkData
import symbol_map
import globals as g
from globals import PATHS, config
import bs4utils
import html_parser
import xml_parser


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


# =============================================================================================== File Utility Functions

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

        xml_parser.process_xml_file_definition(in_path, os.path.join(PATHS["HTML_DEST_PATH"], save_path), file_type)


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
    """ Iterates the HTML directory
    """

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


# =============================================================================================== File Copy Functions

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


# ===============================================================================================

def parse_metadata():

    # meta will use docs_meta as a base and adjust from there
    meta = g.meta.copy()

    # load meta file
    meta_file = utils.parse_xml(config.PROJECT_META_FILE)
    
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
    # generate symbol map from tag file
    g.symbolsMap = symbol_map.generate_map( PATHS["TAG_FILE_PATH"] )

    # copy files from htmlsrc/ to html/
    log("copying files", 0, True)
    copy_files()

    # generate namespace navigation
    g.namespace_nav = bs4utils.generate_namespace_nav()

    log("processing files", 0, True)
    if not g.args.path: # no args; run all docs
        # process_html_dir(PATHS["HTML_SOURCE_PATH"], "html/")
        process_dir( g.XML_ROOT_DIR + os.sep, g.HTML_ROOT_DIR + os.sep )

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
                process_dir(inPath, g.HTML_ROOT_DIR + os.sep)
            log("SUCCESSFULLY GENERATED YOUR FILES!", 0, True)
    else:
        log("Unknown usage", 1, True)
