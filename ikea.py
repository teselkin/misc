#!/usr/bin/python

import urllib2
import re
import simplejson as json

re_productData = r"^\s+var\s+jProductData\s+=\s+(.*);.*"


class ProductData():
    def __init__(self, product_id=None):
        if product_id:
            self.product_id = product_id
            self.data = self.query_data(product_id)
        else:
            self.data = {}
        self.item = self.query_item(product_id, self.data)

    def query_data(self, product_id):
        self.url = "http://www.ikea.com/ru/ru/catalog/products/" + product_id
        try:
            response = urllib2.urlopen(self.url)
        except Exception:
            #print "Not found {}".format(product_id)
            self.url = None
            return {}

        for line in response.readlines():
            match = re.match(re_productData, line)
            if match:
                return json.loads(match.group(1))
        return {}

    def query_item(self, product_id, product_data):
        items = product_data.get('product', {}).get('items', {})
        for item in items:
            if item.get('partNumber').rstrip() == str(product_id).rstrip():
                return item
            else:
                pass
                #print '{} != {}'.format(item.get('partNumber').rstrip(), str(product_id).rstrip())
        return {}

    def __str__(self):
        #print self.item
        if not self.item:
            return '{} ; NOT_FOUND'.format(self.product_id)
        string = '{} ; {} ; {} - {} ; {} ; {}'\
            .format(self.item['partNumber'].encode('utf-8'),
                    self.item['name'].encode('utf-8'),
                    self.item['type'].encode('utf-8'),
                    self.item.get('color', '').encode('utf-8'),
                    self.item['prices']['normal']['priceNormal']['rawPrice'],
                    self.url,
                    )
        return string


with open('shopping_list.txt') as f:
    for line in f:
        #print line
        prod = ProductData(line.rstrip())
        print prod

