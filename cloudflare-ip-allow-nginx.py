#!/usr/bin/env python3

import requests
import re
import os

SIGNATURE = '# Managed by Cloudflare IP Allow Nginx Script'


def fetch_ips(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text.splitlines()
    else:
        return None


def fetch_and_process_all_ips():
    url_v4 = 'https://cloudflare.com/ips-v4'
    url_v6 = 'https://cloudflare.com/ips-v6'
    content_v4 = fetch_ips(url_v4)
    content_v6 = fetch_ips(url_v6)

    if content_v4 is None or content_v6 is None:
        return None

    content = content_v4 + content_v6
    for index, line in enumerate(content):
        content[index] = '    allow ' + line + '; ' + SIGNATURE + '\n'

    content += '    deny all; ' + SIGNATURE + '\n\n'

    return content


def replace_allow_lines(config_file_path, output_path=None):
    with open(config_file_path, 'r') as config_file:
        config_file_lines = config_file.readlines()

    filtered_lines = [line for line in config_file_lines if not line.rstrip().endswith(SIGNATURE)]
    server_find_pattern = r'\s*server\s*\{.*'
    matching_indices = [i for i, s in enumerate(filtered_lines) if re.match(server_find_pattern, s)]

    new_allow_lines = fetch_and_process_all_ips()
    if new_allow_lines is None:
        return

    combined_lines = []
    for index, line in enumerate(filtered_lines):
        combined_lines += line
        if index in matching_indices:
            combined_lines += new_allow_lines

    combined_text = ''.join(combined_lines)
    combined_text = re.sub(r'\n\s*\n+', '\n\n', combined_text)  # Collapse multiple newlines into one

    if output_path is None:
        output_path = config_file_path
    with open(output_path, 'w') as output_file:
        output_file.write(combined_text)


if __name__ == '__main__':
    config_files_dir = '/etc/nginx/http.d/'
    filenames = next(os.walk(config_files_dir), (None, None, []))[2]  # Get filenames of the config files
    conf_filenames = [filename for filename in filenames if filename.endswith('.conf')]  # Get only the config files

    for conf_filename in conf_filenames:
        replace_allow_lines(config_files_dir + conf_filename)

    os.system('service nginx restart')
