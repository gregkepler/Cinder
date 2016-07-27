import os
import json
import codecs
import globals as g

class SearchIndex(object):

	def __init__(self):
		self.index = {"data": []}

	
	def write(self):
	    # save search index to js file
	    document = "var search_index_data = " + json.dumps(self.index).encode('utf-8')
	    # print document
	    if not os.path.exists(os.path.dirname(g.PATHS["HTML_DEST_PATH"] + 'search_index.js')):
	        os.makedirs(os.path.dirname(g.PATHS["HTML_DEST_PATH"] + 'search_index.js'))
	    with codecs.open(g.PATHS["HTML_DEST_PATH"] + 'search_index.js', "w", "UTF-8") as outFile:
	        outFile.write(document)


	def add(self, html, save_path, search_type, tags=[]):
	    """
	    Adds the html page to the search index
	    :param html:
	    :param save_path:
	    :param search_type:
	    :param tags:
	    :return:
	    """

	    # creates new list from tags minus any dupes
	    search_list = list(set(tags))

	    search_obj = {"id": None, "title": None, "tags": []}
	    search_obj["id"] = len(self.index["data"])
	    search_obj["title"] = html.head.find("title").text if html.head.find("title") else ""
	    search_obj["link"] = save_path
	    search_obj["tags"] = search_list
	    search_obj["type"] = search_type
	    self.index["data"].append(search_obj)