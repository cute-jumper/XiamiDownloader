#! /usr/bin/env python
#-*- coding: utf-8 -*-
# Author: qjp
# Date: <2013-05-13 Mon>

from __future__ import division
import sys, math, urllib, urllib2, time
from xml.dom.minidom import parse
from itertools import izip_longest, takewhile
from operator import add
from bs4 import BeautifulSoup as BS

search_url_template = 'http://www.xiami.com/search?key={keyword}'
search_result_classes = [u'song_name', u'song_artist', u'song_album']
search_result_classes_zh = [u'歌曲', u'歌手', u'专辑']
search_result_col_width = 20

xml_url_template = 'http://www.xiami.com/song/playlist/id/{song_id}/object_name/default/object_id/0'
xml_tagname_list = ['title', 'artist', 'location', 'lyric', 'pic']

request_headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:20.0) Gecko/20100101 Firefox/20.0'}

def xiami_urlopen(url):
    '''Xiami will not allow using bare urlopen.
    We have to add headers to the request.'''
    req = urllib2.Request(url, headers=request_headers)
    return urllib2.urlopen(req)

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

def parse_song_info(song_id):
    '''Parse song information according to the song_id'''
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

def search_xiami(keyword):
    '''Search http://www.xiami.com and return search results'''
    search_url = search_url_template.format(keyword=keyword)
    soup = BS(xiami_urlopen(search_url).read())
    box = soup.find('div', {'class': 'search_result_box'})
    # Get all song ids
    song_ids = map(lambda x: (int)(x.children.next()['value']),
                   box.find_all('td', {'class': 'chkbox'}))
    # Get all song texts
    elems = [map(lambda elem: elem.text, box.find_all('td', {'class': classname}))
             for classname in search_result_classes]
    return song_ids, zip(*elems)

def output_song_info(song_info):
    for i in xml_tagname_list:
        print '\033[1;36m[' + i + ']:\033[0m ' + song_info[i]
    print

def output_search_results(results):
    # Helper functions for output only
    import unicodedata
    def display_len(s):
        return sum(map(lambda x: 2 if unicodedata.east_asian_width(x) == 'W' or
                       unicodedata.east_asian_width(x) == 'F'
                       else 1, s))
    def scanl(f, acc, l):
        for x in l:
            acc = f(acc, x)
            yield acc
    def get_display_len_array(text):
        return [0] + list(scanl(add, 0, map(display_len, text)))
    def get_row_text_generator(text, display_len_array):
        '''Return the generator for a certain column'''
        def get_row_text():
            start = 0
            while start < len(display_len_array) - 1:
                length_array = list(takewhile(lambda x: x - display_len_array[start] <=
                                              search_result_col_width, display_len_array[start:]))
                end = start + len(length_array) - 1
                ret = text[start:end]
                start = end
                yield ret + ' ' * (search_result_col_width - display_len(ret))
            while True:
                yield blank_cell
        return get_row_text()
    def build_line(beginning, conjuction, ending, lst):
        return beginning + conjuction.join(lst) + ending
    # Helper functions end
    max_num_len = len(str(len(results)))
    if max_num_len < 2:
        max_num_len = 2
    horizon_line = build_line('|-', '-+-', '-|', ['-' * max_num_len] +
                              ['-' * search_result_col_width] * len(search_result_classes))
    celling_line = floor_line = build_line('--', '---', '--', ['-' * max_num_len] +
                                           ['-' * search_result_col_width] * len(search_result_classes))
    blank_cell = ' ' * search_result_col_width
    print celling_line
    print build_line('| ', ' | ', ' |', ['No%s' %(' ' * (max_num_len - 2))] +
                     [i + (search_result_col_width - display_len(i)) * ' '
                      for i in search_result_classes_zh])
    for row_num, res in enumerate(results, 1):
        print horizon_line
        row_text_generators = map(lambda x: get_row_text_generator(x, get_display_len_array(x)), res)
        is_first = True
        while True:
            col_text_array = map(lambda x: x.next(), row_text_generators)
            if len(filter(lambda x: x != blank_cell, col_text_array)) > 0:
                if is_first:
                    print build_line('| ', ' | ', ' |', ['%d%s' %(row_num, ' ' * (max_num_len - len(str(row_num))))]
                                     + col_text_array)
                    is_first = False
                else:
                    print build_line('| ', ' | ', ' |', ['%s' %(' ' * max_num_len)] + col_text_array)
            else:
                break
    print floor_line
    
def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        return result, te - ts
    return timed

def humanize_bytes(bytes, precision=1):
    """Copied from
    http://code.activestate.com/recipes/577081-humanized-representation-of-a-number-of-bytes/"""
    abbrevs = (
        (1<<50L, 'PB'),
        (1<<40L, 'TB'),
        (1<<30L, 'GB'),
        (1<<20L, 'MB'),
        (1<<10L, 'kB'),
        (1, 'B')
    )
    if bytes == 1:
        return '1 byte'
    for factor, suffix in abbrevs:
        if bytes >= factor:
            break
    return '%.*f %s' % (precision, bytes / factor, suffix)

# My exceptions
class InputException(Exception):
    pass
class NumberRangeException(Exception):
    pass

def get_user_input():
    while True:
        try:
            user_input = raw_input('Please input a song number("q" to quit): ')
            if user_input.lower() == 'q':
                raise InputException()
            else:
                sel_num = int(user_input)
                if 1 <= sel_num <= len(search_results):
                    break
                raise NumberRangeException()
        except (KeyboardInterrupt, InputException):
            sys.exit(1)
        except NumberRangeException:
            print "Error. Please input a number between {low} and {high}!".format(low=1, high=len(search_results))
        except:
            print "Error. Please input a number again!"
    return sel_num

def download_music(sel_result, sel_id):
    def download_progress(count, block_size, total_size):
        total_len = 41
        percent = int(count * block_size * 100 / total_size)
        finished = '-' * int(percent / 100.0 * (total_len - 1)) + '>'
        unfinished = ' ' * (total_len - len(finished))
        sys.stdout.write(chr(27) + '[2K') # clear to end of line, interesting
        sys.stdout.write("\r%3d%% [%s%s] [%s]" %(percent, finished, unfinished,
                                                 humanize_bytes(count * block_size)))
        sys.stdout.flush()
    saved_file_name = "%s-%s.mp3" %(sel_result[0], sel_result[1])
    (retrieve_ret, used_time) = timeit(urllib.urlretrieve)(parse_song_info(sel_id)['location'],
                                                          saved_file_name,
                                                          download_progress)
    download_size = long(retrieve_ret[1]['content-length'])
    print '\nFetched %s in %.1fs (%s/s)' %(humanize_bytes(download_size),
                                           used_time,
                                           humanize_bytes(1.0 * download_size / used_time))
    print "Saved to file '%s'" %saved_file_name

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print '\033[0;32m[Usage]:\033[0m python ' + __file__ + " keyword"
        sys.exit(1)
    (result_ids, search_results) = search_xiami(sys.argv[1])
    if len(search_results) == 0:
        print 'No results found!'
        sys.exit(0)
    output_search_results(search_results)
    sel_num = get_user_input()
    sel_result = search_results[sel_num - 1]
    sel_id = result_ids[sel_num - 1]
    download_music(sel_result, sel_id)
