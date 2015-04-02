# -*- coding: utf-8 -*-
import requests
import re

from pymongo import MongoClient
from BeautifulSoup import BeautifulSoup
from slugify import slugify
from bson import json_util

import mechanize

# Connect to defualt local instance of MongoClient
client = MongoClient()

# Get database and collection
db = client.arcas

def scrape():

    db.assetsandincomes.remove({})

    br = mechanize.Browser()
    br.set_handle_robots(False)   # ignore robots
    br.set_handle_refresh(False)  # can sometimes hang without this
    br.addheaders = [('User-agent', 'Firefox')]

    search_post_req_url = "http://www.acas.rs/acasPublic/imovinaFunkcioneraSearch.htm"
    search_post_req_payload = {
        'sEcho': 3,
        'iColumns': 3,
        'sColumns': '',
        'iDisplayStart':0,
        'iDisplayLength':10,
        'mDataProp_0':0,
        'mDataProp_1':1,
        'mDataProp_2':2,
        'prezime': '',
        'ime': '',
    }

    
    r = requests.post(search_post_req_url, data=search_post_req_payload)
    json_resp = r.json()

    data_list = json_resp['aaData']

    for data in data_list:

        fullname = data[0]

        functions = data[1] \
            .replace('<span onmouseover="textUnderline(this);" onmouseout="textNormal(this);" >', '') \
            .replace('</span>', '') \
            .strip() \
            .split('<br>')

        # Get the report IDs for the result row, can be multiple
        regex = re.compile(r"\(\d+\)")
        matches = regex.findall(data[2])

        # For each report ID, fetch the page.
        for match in matches:
            report_id = match. \
                replace('(', ''). \
                replace(')', '')

            details_get_req_url = "http://www.acas.rs/acasPublic/izvestajDetails.htm?parent=pretragaIzvestaja&izvestajId=%s" % report_id

            report_page = br.open(details_get_req_url)

            report_page_html_str = report_page.read()
            report_page_soup = BeautifulSoup(report_page_html_str)

            data_tables = report_page_soup.findAll('table')

            assets_and_incomes_table = data_tables[2]
            assets_and_incomes_table_rows = assets_and_incomes_table.findAll('tr')

            prop_names = []

            for row_index, row in enumerate(assets_and_incomes_table_rows):

                # Init report doc.
                # TODO: Add date.
                doc = {
                    'fullname': fullname,
                    'functions': functions,
                    'izvestajId': int(report_id),
                    'properties': []
                }

                # Get property names from table header
                if row_index == 0:
                    header_cells = row.findAll('th')
                    for header_cell in header_cells:
                        prop_names.append(header_cell.text)
                
                # Get property values for each row
                else:
                    for column_index, cell in enumerate(row.findAll('td')):
                        
                        prop_name = prop_names[column_index]
                        print '%s: %s' % (prop_name, cell.text)

                        # Create subdoc for the report doc
                        doc['properties'].append({
                            'property': prop_name,
                            'value': cell.text
                        })

                    
                    # Save doc in database.
                    # WARNING: We don't create a doc with the entire table date on it.
                    # We create one doc per table row.
                    # Can change this structure if we want.
                    db.assetsandincomes.insert(doc)
                    

            # In the future, will have to consider the number of data tables
            '''
            if len(data_tables) == 8:

            elif len(data_tables) == 9:

            else:
                print 'Invalid number of data tables'
            '''

# Let's scrape.
scrape()