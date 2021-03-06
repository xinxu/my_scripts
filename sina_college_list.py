# -*- coding: utf-8 -*-
# standard libs
import urllib, urllib2, re, json
# custom libs
import requests
from anjuke import pinyin
from lxml.html import fromstring
next_page_str = u"\u4e0b\u4e00\u9875"
max_provid = 32
pinyin_c = pinyin.Converter()

YOUR_AVOS_APP_ID = ''
YOUR_AVOS_APP_KEY = ''

def parse_school_name(node):
	a_list = node.xpath('./a')
	n = node if len(a_list) == 0 else a_list[0]
	return n.text_content()


def parse_school_node(node):
	td_list = node.xpath('./td')
	name = parse_school_name(td_list[0])
	location = td_list[1].text_content()
	category = td_list[2].text_content()
	level = td_list[5].text_content()
	fl = pinyin_c.convert(name, fmt='fl', sc=False)
	fpy = pinyin_c.convert(name, sc=False)
	return {'name': name, 'location': location, 'category': category, 'level': level, 'firstletter': fl, 'pinyin': fpy}

def parse_page(provid, page):
	url = 'http://kaoshi.edu.sina.com.cn/collegedb/collegelist.php?provid={0}&page={1}'.format(provid, page)
	content = urllib.urlopen(url).read()
	doc = fromstring(content.decode('gb2312'));
	school_list = doc.xpath('//tr[@class="tr2"]|//tr[@class="tr3"]')
	next_page_xpath_express = u'//a[@title="{0}"]'.format(next_page_str)
	next_page = doc.xpath(next_page_xpath_express)
	li = list()
	for node in school_list:
		li.append(parse_school_node(node))
	return (li, len(next_page) > 0)

def parse_prov(provid):
	li = list()
	page = 1
	while True:
		result = parse_page(provid, page)
		li.extend(result[0])
		if (result[1]):
			page = page + 1
		else:
			print 'provid {0} has {1} schools'.format(provid, len(li))
			return li

def create_avos_college(college_dict):
	url = 'https://cn.avoscloud.com/1/classes/College'
	headers = {'X-AVOSCloud-Application-Id': YOUR_AVOS_APP_ID, \
	 'X-AVOSCloud-Application-Key': YOUR_AVOS_APP_ID, \
	  'Content-Type': 'application/json'}
	print college_dict
	r = requests.post(url, json.dumps(college_dict), headers=headers)
	print r.text

if __name__ == '__main__':
	li = list()
	for x in xrange(1, max_provid + 1):
		li.extend(parse_prov(x))
	for idx, c in enumerate(li):
		c['cid'] = idx + 1001;
	print len(li)
	with open('college_list.json', 'w') as outfile:
		json.dump(li, outfile)
	for c in li:
		create_avos_college(c)
