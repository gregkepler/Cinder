#! /usr/bin/python
import sys
import re
import xml.etree.ElementTree as ET
import globals
# from globals import args


# =============================================================================================== Logging
def log(message, level=0, force=False):   
    if globals.args.debug or force:

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