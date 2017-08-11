#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET

import cerberus

import schema

OSM_PATH = "san-jose_california.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWERUPPER_COLON = re.compile(r'^([a-zA-Z]|_)+:([a-zA-Z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)

SCHEMA = schema.schema

# The fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


expected_streetnames = ["Avenue", "Boulevard","Street","Drive","Place","Lane","Way","Court","Circle","Road","Alameda",
			"Terrace","Alley","Madrid","Barcelona","East","Palamos","Marino","Napoli","Portofino","Sorrento","Parkway",
			"Luna","Square","Julian","Real","Presada","Highway","Seville","Loop","Expressway","West","Plaza",
			"Volante","Hill","Franklin"]


mapping_streetnames = { "Blvd": "Boulevard","Blvd.":"Boulevard","Ave":"Avenue","ave":"Avenue","St":"Street",
						"street":"Street","Dr":"Drive","Rd":"Road","Ct":"Court","Hwy":"Highway","Ln":"Lane",
						"Cir":"Circle","Sq":"Square"}

expected_state="CA"
def update_state(state):
	"""If state is "ca"|"california"|"California"|"Ca" it will be replaced with "CA" """
	if state=="ca" or state=="california" or state=="California" or state=="CA" or state=="Ca":
		return expected_state
	else:
		return expected_state
		
		
def update_street_name(name, mapping_streetnames):
	"""Extracts last part of street name if it satisfies street_type_re regular expression
	   and maps with its respective mapping_streetnames  
	"""    
    n = street_type_re.search(name)
    if n:
		update_street_type = n.group()
		if update_street_type in mapping_streetnames:
			update_street_name=name.strip(update_street_type)
			name=update_street_name+mapping_streetnames[update_street_type]
    return name		
		
def update_postcode(postcode): 
	"""If postal code is appended with state abbreviation it will be stripped off"""
    print (postcode)
    if (postcode.find("CA")==0):
        update_postcode=postcode.strip("CA").strip()
    elif (postcode=="CUPERTINO"):
        update_postcode="95014"
    else:
        update_postcode=postcode
    print (update_postcode)
    return update_postcode

def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
	"""Takes in each node or way and forms its respective dictionary """
	
	node_attribs = {}
	way_attribs = {}
	way_nodes = []
	tags = []  # Handle secondary tags the same way for both node and way elements

	if element.tag == 'node':
		node_attribs['id']=element.attrib['id']
		node_attribs['user']=element.attrib['user']
		node_attribs['uid']=element.attrib['uid']
		node_attribs['version']=element.attrib['version']
		node_attribs['lat']=element.attrib['lat']
		node_attribs['lon']=element.attrib['lon']
		node_attribs['timestamp']=element.attrib['timestamp']
		node_attribs['changeset']=element.attrib['changeset']
		node_child=element.find('tag')
		if node_child != None:
			for tag in element.findall('tag'):
				test={}
				test['id']=element.attrib['id']
				if PROBLEMCHARS.match(tag.attrib["k"]):
					continue
                   
				elif LOWERUPPER_COLON.match(tag.attrib["k"]):
					
					test["type"] = tag.attrib["k"].split(":", 1)[0]
					
					test["key"] = tag.attrib["k"].split(":", 1)[1]
					if tag.attrib["k"] == 'addr:street':
						test['value']=update_street_name(tag.attrib["v"], mapping_streetnames)
					elif tag.attrib["k"] == 'addr:state':
						test['value']=update_state(tag.attrib["v"])	
					elif tag.attrib["k"] == 'addr:postcode':
						test['value']=update_postcode(tag.attrib["v"])
					else:
						test['value']=tag.attrib["v"]
				else:
					test['type']='regular'
					test['key']=tag.attrib['k']
					test['value']=tag.attrib["v"]	
				#print test
				tags.append(test)
		
		
		return {'node': node_attribs, 'node_tags': tags}
	elif element.tag == 'way':
		way_attribs['id']=element.attrib['id']
		way_attribs['user']=element.attrib['user']
		way_attribs['uid']=element.attrib['uid']
		way_attribs['version']=element.attrib['version']
		way_attribs['timestamp']=element.attrib['timestamp']
		way_attribs['changeset']=element.attrib['changeset']
		way_child=element.find('tag')
		if way_child != None:
			for tag in element.findall('tag'):
				test={}
				test['id']=element.attrib['id']
				if PROBLEMCHARS.match(tag.attrib["k"]):
					continue			
				elif LOWERUPPER_COLON.match(tag.attrib["k"]):
					test["type"] = tag.attrib["k"].split(":", 1)[0]
					test["key"] = tag.attrib["k"].split(":", 1)[1]
					if tag.attrib["k"] == 'addr:street':
						test['value']=update_street_name(tag.attrib["v"], mapping_streetnames)
					elif  tag.attrib["k"] == 'addr:state':
						test['value']=update_state(tag.attrib["v"])
					elif tag.attrib["k"] == 'addr:postcode':
						test['value']=update_postcode(tag.attrib["v"])	
					else:
						test['value']=tag.attrib["v"]
				else:
					test['type']='regular'
					test['key']=tag.attrib['k']
					test['value']=tag.attrib["v"]
						
				tags.append(test)
		way_node_child=element.find('nd')
		if way_node_child != None:
			i=0
			for tag in element.findall('nd'):
				test={}
				test['id']=element.attrib['id']
				test['node_id']=tag.attrib['ref']
				test['position']=i
				way_nodes.append(test)
				i=i+1
                
		return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
	"""Iteratively process each XML element and write to csv(s)"""

	with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

		nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
		node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
		ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
		way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
		way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

		nodes_writer.writeheader()
		node_tags_writer.writeheader()
		ways_writer.writeheader()
		way_nodes_writer.writeheader()
		way_tags_writer.writeheader()

		validator = cerberus.Validator()
		for element in get_element(file_in, tags=('node', 'way')):
			el = shape_element(element)
			#print el
			if el:
				if validate is True:
					validate_element(el, validator)

				if element.tag == 'node':
					nodes_writer.writerow(el['node'])
					node_tags_writer.writerows(el['node_tags'])
				elif element.tag == 'way':
					ways_writer.writerow(el['way'])
					way_nodes_writer.writerows(el['way_nodes'])
					way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    process_map(OSM_PATH, validate=True)
