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
parser.add_argument('target_folder', nargs='?', default=os.getcwd(), help='folder where the media will be stored')
parser.add_argument('-o', '--output', choices=['save', 'wget', 'ssh', 'test', 'curl'], help='output format')
parser.add_argument('--ssh', help='if output is ssh, you need to give your user@localhost server address')
parser.add_argument('-b', '--blindness', action='store_true', help='show videos with "Hörfassung" in title (disabled by default)')
parser.add_argument('-n', '--not_search', help='words you want to exclude from result, for example "Hörfassung" (separate multiple by commata)')
parser.add_argument('-v', '--verbose', action='store_true', help='show verbose output')
parser.add_argument('-t', '--test', action='store_true', help='just show list of titles')
arguments = parser.parse_args()


class MVW:
    feed_url = 'https://mediathekviewweb.de/feed?query=%s'
    search_string = None
    remove_search_list = list()
    target_folder = None
    show_blindness_version = False
    output_type = 'save'
    verbose = False
    ssh = None
    feed = None

    def __init__(self, args):
        # todo: create check_and_get methods for all of them
        self.search_string = args.search_string
        self.target_folder = args.target_folder
        self.show_blindness_version = args.blindness
        self.ssh = args.ssh if args.ssh else self.ssh
        self.verbose = args.verbose
        self.output_type = args.output if args.output else self.output_type
        self.output_type = 'test' if args.test else self.output_type
        self.remove_search_list = [x.strip() for x in args.not_search.split(',')] if args.not_search else self.remove_search_list
        self.main()

    def main(self):
        self.feed = feedparser.parse(self.feed_url % urllib.parse.quote(self.search_string))
        print('### dealing with %i medias' % len(self.feed['items']))
        for item in self.feed['items']:
            if self.remove_from_result(item):
                continue
            self.parse_item(item)
        print('### dealed with %i medias' % len(self.feed['items']))

    def remove_from_result(self, item):
        if not self.show_blindness_version and 'Hörfassung' in item['title']:
            return True
        elif any(word in item['title'] for word in self.remove_search_list):
            return True
        else:
            return False

    def parse_item(self, item):
        self.print_item_header(item)
        output = {
            'save': self.output_save,
            'ssh': self.output_ssh,
            'curl': self.output_curl,
            'wget': self.output_wget,
            'test': self.output_test,
        }
        output[self.output_type](item)

    def print_item_header(self, item):
        target_filepath, target_filename = self.get_target_data(item)
        print()
        print('[%s] ' % item['authors'][0]['name'], end='')
        print('[%s] ' % str(datetime.timedelta(seconds=int(item['duration']))), end='')
        print(item['title'], end='')
        print()
        print('--> ', os.path.join(target_filepath, target_filename))

    def output_save(self, item):
        target_filepath, target_filename = self.get_target_data(item)
        os.makedirs(target_filepath)
        target_file = os.path.join(target_filepath, target_filename)

        response = requests.get(item['link'], stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        transfer = tqdm(total=total_size, unit='iB', unit_scale=True)
        with open(target_file, 'wb') as file:
            for data in response.iter_content(block_size):
                transfer.update(len(data))
                file.write(data)
        transfer.close()
        if total_size != 0 and transfer.n != total_size:
            logging.error("error while downloading")

    def output_ssh(self, item):
        target_filepath, target_filename = self.get_target_data(item)
        target_filepath = target_filepath.replace(' ', '\\ ')
        target_filename = target_filename.replace(' ', '\\ ')
        os.system('ssh %s mkdir -p "%s"' % (self.ssh, target_filepath))
        os.system('ssh %s wget %s -O "%s"' % (self.ssh, item['link'], os.path.join(target_filepath, target_filename)))
        # hack to make it possible to exit with strg+c
        print()
        print('### sleeping for 5 seconds, use strg+c now if neccessary')
        time.sleep(3)

    def output_curl(self, item):
        target_filepath, target_filename = self.get_target_data(item)
        target_filepath = target_filepath.replace(' ', '\\ ')
        target_filename = target_filename.replace(' ', '\\ ')
        os.system('ssh %s mkdir -p "%s"' % (self.ssh, target_filepath))
        os.system('ssh %s curl %s -# -o "%s"' % (self.ssh, item['link'], os.path.join(target_filepath, target_filename)))
        # hack to make it possible to exit with strg+c
        print()
        print('### sleeping for 5 seconds, use strg+c now if neccessary')
        time.sleep(3)

    def output_wget(self, item):
        target_filepath, target_filename = self.get_target_data(item)
        print('mkdir -p "%s"' % target_filepath)
        print('wget %s -O "%s"' % (item['link'], os.path.join(target_filepath, target_filename)))

    def output_test(self, item):
        pass

    def get_target_data(self, item):
        series_data = re.findall(r'(.+)\((\d+)/(\d+)\)\W*(.+)', item['title'])
        if series_data:
            target_path, target_filename = self.get_series_target_filename(series_data[0])
        else:
            target_path = item['title']
            target_filename = item['title']
        target_filename = self.sanitize(target_filename + self.get_extension(item['link']))
        target_filepath = self.sanitize(os.path.join(self.target_folder, target_path))
        return target_filepath, target_filename

    def get_extension(self, url):
        source_filename, extension = os.path.splitext(url)
        return extension

    def sanitize(self, string):
        string = string.replace(':', '-')
        string = string.replace('|', '-')
        string = string.replace('(', '_')
        string = string.replace(')', '_')
        return string

    def get_series_target_filename(self, series_data):
        series_title = series_data[0].strip()
        episode_title = series_data[3].strip()
        season_num = int(series_data[2])
        episode_num = int(series_data[1])
        target_path = os.path.join(series_title, 'Season %02d' % 1)
        target_filename = '%s - s%02de%02d - %s' % (series_title, season_num, episode_num, episode_title)
        return target_path, target_filename


MVW(arguments)
