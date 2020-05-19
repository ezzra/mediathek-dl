# -*- coding: utf-8 -*-
import feedparser
import re
import os
import urllib.parse
import argparse
from tqdm import tqdm
import requests
import logging
import datetime
import time


parser = argparse.ArgumentParser()
parser.add_argument('search_string', help='the search string for the medias you want to download')
parser.add_argument('-f', '--folder', help='folder where the media will be stored')
parser.add_argument('-o', '--output', choices=['save', 'wget', 'test', 'curl'], help='output format')
parser.add_argument('--ssh', help='set this to tunnel your curl or wget output through ssh')
parser.add_argument('-b', '--blindness', action='store_true', help='show videos with "Hörfassung" in title (disabled by default)')
parser.add_argument('-n', '--not_search', help='words you want to exclude from result, for example "Hörfassung" (separate multiple by commata)')
parser.add_argument('--wget', help='options for wget command')
parser.add_argument('--curl', help='options for curl command')
parser.add_argument('-v', '--verbose', action='store_true', help='show verbose output')
parser.add_argument('-t', '--test', action='store_true', help='just show list of titles')
parser.add_argument('-p', '--printonly', action='store_true', help='just print the commands without executing (for wget and curl output)')
arguments = parser.parse_args()


class MVW:
    feed_url = 'https://mediathekviewweb.de/feed?query=%s'
    search_string = None
    remove_search_list = list()
    target_folder = os.getcwd()
    show_blindness_version = False
    blindness_list = ['Hörfassung', 'Hörfilm']
    output_type = 'save'
    verbose = False
    ssh = None
    feed = None
    printonly = False
    wget_options = ''
    curl_options = ''

    def __init__(self, args):
        # todo: create check_and_get methods for all of them
        self.search_string = args.search_string
        self.target_folder = args.folder if args.folder else self.target_folder
        self.show_blindness_version = args.blindness
        self.printonly = args.printonly
        self.ssh = args.ssh if args.ssh else self.ssh
        self.wget_options = args.wget if args.wget else self.wget_options
        self.curl_options = args.curl if args.curl else self.curl_options
        self.verbose = args.verbose
        self.output_type = args.output if args.output else self.output_type
        self.output_type = 'test' if args.test else self.output_type
        self.remove_search_list = [x.strip() for x in args.not_search.split(',')] if args.not_search else self.remove_search_list
        self.main()

    def main(self):
        self.feed = feedparser.parse(self.feed_url % urllib.parse.quote(self.search_string))
        for item in self.feed['items']:
            if self.remove_from_result(item):
                continue
            self.parse_item(item)

    def remove_from_result(self, item):
        if not self.show_blindness_version and any(word in item['title'] for word in self.blindness_list):
            return True
        elif any(word in item['title'] for word in self.remove_search_list):
            return True
        else:
            return False

    def parse_item(self, item):
        self.print_item_header(item)
        output = {
            'save': self.output_save,
            'curl': self.output_curl,
            'wget': self.output_wget,
            'test': self.output_test,
        }
        # noinspection PyArgumentList
        output[self.output_type](item)

    def print_item_header(self, item):
        if self.printonly:
            return
        target_data = self.get_target_data(item)
        print()
        print('[%s] ' % item['authors'][0]['name'], end='')
        print('[%s] ' % str(datetime.timedelta(seconds=int(item['duration']))), end='')
        print(item['title'], end='')
        print()
        print('--> ', os.path.join(target_data['filepath'], target_data['filename']))

    def output_save(self, item):
        target_data = self.get_target_data(item)
        os.makedirs(target_data['filepath'])
        response = requests.get(item['link'], stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        transfer = tqdm(total=total_size, unit='iB', unit_scale=True)
        with open(target_data['joined_path'], 'wb') as file:
            for data in response.iter_content(block_size):
                transfer.update(len(data))
                file.write(data)
        transfer.close()

    def output_wget(self, item):
        target_data = self.get_target_data(item)
        ssh_cmd, target_data = self.get_ssh_cmd(target_data)
        mkdir_cmd = '%smkdir -p "\'%s\'"' % (ssh_cmd, target_data['filepath'])
        wget_cmd = '%swget %s -C -O %s "\'%s\'"' % (ssh_cmd, item['link'], self.wget_options, target_data['joined_path'])
        if self.printonly:
            print()
            print(mkdir_cmd)
            print(wget_cmd)
        else:
            os.system(mkdir_cmd)
            os.system(wget_cmd)
            # hack to make it possible to exit with strg+c
            print()
            print('### sleeping for 5 seconds, use strg+c now if neccessary')
            time.sleep(5)

    def output_curl(self, item):
        target_data = self.get_target_data(item)
        ssh_cmd, target_data = self.get_ssh_cmd(target_data)
        mkdir_cmd = '%smkdir -p "%s"' % (ssh_cmd, target_data['filepath'])
        curl_cmd = '%scurl %s -C - -# %s -o "%s"' % (ssh_cmd, item['link'], self.curl_options, target_data['joined_path'])
        if self.printonly:
            print()
            print(mkdir_cmd)
            print(curl_cmd)
        else:
            os.system(mkdir_cmd)
            os.system(curl_cmd)
            # hack to make it possible to exit with strg+c
            print()
            print('### sleeping for 5 seconds, use strg+c now if neccessary')
            time.sleep(5)

    def output_test(self, item):
        pass

    def get_ssh_cmd(self, target_data):
        if self.ssh:
            target_data['filename'] = target_data['filename'].replace(' ', '\\ ')
            target_data['filepath'] = target_data['filepath'].replace(' ', '\\ ')
            target_data['joined_path'] = target_data['joined_path'].replace(' ', '\\ ')
            ssh_cmd = ('ssh %s ' % self.ssh)
        else:
            ssh_cmd = ''
        return ssh_cmd, target_data

    def get_target_data(self, item):
        series_data = re.findall(r'(.+)\((\d+)/(\d+)\)\W*(.*)', item['title'])
        if series_data:
            target_data = self.get_series_target_data(series_data[0])
        else:
            target_data = dict()
            target_data['filename'] = item['title']
            target_data['filepath'] = item['title']

        target_data['filename'] = self.sanitize(target_data['filename'] + self.get_extension(item['link']))
        target_data['filepath'] = self.sanitize(os.path.join(self.target_folder, target_data['filepath']))
        target_data['joined_path'] = os.path.join(target_data['filepath'], target_data['filename'])

        return target_data

    def get_extension(self, url):
        source_filename, extension = os.path.splitext(url)
        return extension

    def sanitize(self, string):
        string = string.replace(':', '-')
        string = string.replace('|', '-')
        string = string.replace('(', '_')
        string = string.replace(')', '_')
        string = string.replace('&', '+')
        string = string.replace('"', '')
        string = string.replace('\'', '')
        string = re.sub(r' - Staffel \d', '', string)
        return string

    def get_series_target_data(self, series_data):
        series_title = series_data[0].strip()
        episode_title = series_data[3].strip()
        season_num = self.get_season_num(series_title)
        episode_num = int(series_data[1])
        target_data = dict()
        target_data['filepath'] = os.path.join(series_title, 'Season %02d' % season_num)
        target_data['filename'] = '%s - s%02de%02d' % (series_title, season_num, episode_num)
        if episode_title:
            target_data['filename'] = target_data['filename'] + ' - ' + episode_title
        return target_data

    def get_season_num(self, series_title):
        season_num = re.findall(r'Staffel (\d)', series_title)
        if season_num:
            return int(season_num[0])
        return 1


MVW(arguments)
