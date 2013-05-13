#! /usr/bin/env python
#-*- coding: utf-8 -*-
# Author: qjp
# Date: <2013-05-13 Mon>

import sys, math, urllib, urllib2
from xml.dom.minidom import parse
from itertools import izip_longest, takewhile, ifilter
from operator import add
from bs4 import BeautifulSoup as BS

search_url_template = 'http://www.xiami.com/search?key={keyword}'
search_result_classes = [u'song_name', u'song_artist', u'song_album']
search_result_classes_zh = [u'歌曲', u'歌手', u'专辑']
search_result_col_width = 20
xml_url_template = 'http://www.xiami.com/song/playlist/id/{song_id}/object_name/default/object_id/0'
xml_tagname_list = ['title', 'artist', 'location', 'lyric', 'pic']
request_headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:20.0) Gecko/20100101 Firefox/20.0'}


def decode_location(loc):
    '''Decode the location. Just `transpose' the matrix'''
    row = (int)(loc[0])
    ciphertext = loc[1:]
    col = (int)(math.floor(len(ciphertext) / row))
    rem = len(ciphertext) % row
    row_text = [' '] * row
    for i in range(0, rem):
        begin_index = (col + 1) * i
        row_text[i] = ciphertext[begin_index:begin_index + col + 1]
    for i in range(rem, row):
        begin_index = col * (i - rem) + (col + 1) * rem
        row_text[i] = ciphertext[begin_index:begin_index + col]
    clear_text = ''.join(map(''.join, izip_longest(*row_text, fillvalue='')))
    real_url = urllib.unquote(clear_text).replace('^', '0').replace('+', ' ')
    return real_url

def xiami_urlopen(url):
    req = urllib2.Request(url, headers=request_headers)
    return urllib2.urlopen(req)

def parse_song_info(song_id):    
    def get_text(nodelist):
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE or node.nodeType == node.CDATA_SECTION_NODE:
                rc.append(node.data)
        return ''.join(rc)
    xml_url = xml_url_template.format(song_id=song_id)
    xml_dom = parse(xiami_urlopen(xml_url))
    node_dict = {tagname: get_text(xml_dom.getElementsByTagName(tagname)[0].childNodes)
                 for tagname in xml_tagname_list}
    node_dict['location'] = decode_location(node_dict['location'])
    return node_dict

def output_song_info(song_info):
    for i in xml_tagname_list:
        print '\033[1;36m[' + i + ']:\033[0m ' + song_info[i]
    print
    
def output_search_results(results):
    max_num_len = len(str(len(results)))
    if max_num_len < 2:
        max_num_len = 2
    horizon_line = '|-' + '-' * max_num_len + '-+-' + '-+-'.join(['-' * search_result_col_width] * len(search_result_classes)) + '-|'
    end_line = '--' + '-' * max_num_len + '---' + '---'.join(['-' * search_result_col_width] * len(search_result_classes)) + '--'
    blank_cell = ' ' * search_result_col_width
    import unicodedata
    def display_len(s):
        return sum(map(lambda x: 2 if unicodedata.east_asian_width(x) == 'W' or unicodedata.east_asian_width(x) == 'F'
                       else 1, s))
    def scanl(f, acc, l):
        for x in l:
            acc = f(acc, x)
            yield acc
    def get_display_len_array(text):
        return [0] + list(scanl(add, 0, map(display_len, text)))
    def get_row_text_generator(text, display_len_array):
        def get_row_text():
            start = 0
            while start < len(display_len_array) - 1:
                length_array = list(takewhile(lambda x: x - display_len_array[start] <= search_result_col_width, display_len_array[start:]))
                end = start + len(length_array) - 1
                ret = text[start:end]
                start = end
                yield ret + ' ' * (search_result_col_width - display_len(ret))
            while True:
                yield blank_cell
        return get_row_text()
    print end_line
    print '| No | ' + ' | '.join([i + (search_result_col_width - display_len(i)) * ' '
                          for i in search_result_classes_zh]) + ' |'
    
    for row_num, res in enumerate(results, 1):
        print horizon_line
        row_text_generators = map(lambda x: get_row_text_generator(x, get_display_len_array(x)), res)
        is_first = True
        while True:
            col_text_array = map(lambda x: x.next(), row_text_generators)
            if len(filter(lambda x: x != blank_cell, col_text_array)) > 0:
                if is_first:
                    print '| %d%s | ' %(row_num, ' ' * (max_num_len - len(str(row_num)))) + ' | '.join(col_text_array) + ' |'
                    is_first = False
                else:
                    print '| %s | ' %(' ' * max_num_len) + ' | '.join(col_text_array) + ' |'
            else:
                break
    print end_line
            
def search_xiami(keyword):
    search_url = search_url_template.format(keyword=keyword)
    soup = BS(xiami_urlopen(search_url).read())
    box = soup.find('div', {'class': 'search_result_box'})
    chkboxes = box.find_all('td', {'class': 'chkbox'})
    elems = [map(lambda elem: elem.text, box.find_all('td', {'class': classname})) for classname in search_result_classes]
    return map(lambda x: (int)(x.children.next()['value']), chkboxes), zip(*elems)
    
if __name__ == '__main__':
    (result_ids, search_results) = search_xiami('谢安琪')
    output_search_results(search_results)
    while True:
        input_num = (int)(raw_input('Please select a number: '))
        if input_num < 1 or input_num > len(search_results):
            print "Error. Please select a number again!"
        else:
            break
    sel = search_results[input_num - 1]
    print 'Begin downloading file...'
    urllib.urlretrieve(parse_song_info(result_ids[input_num - 1])['location'], "%s_%s.mp3" %(sel[0], sel[1]))
    print 'Finished!'
    
