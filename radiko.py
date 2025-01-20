import urllib.request, urllib.error, urllib.parse
import os, sys, argparse, re
import base64
import logging
import xml.etree.ElementTree as ET

auth_key = "bcd151073c03b352e1ef2fd66c32209da9ca0afa"

def auth1():
    url = "https://radiko.jp/v2/api/auth1"
    headers = {
        "User-Agent": "curl/7.56.1",
        "Accept": "*/*",
        "X-Radiko-App": "pc_html5",
        "X-Radiko-App-Version": "0.0.1",
        "X-Radiko-User": "dummy_user",
        "X-Radiko-Device": "pc",
    }
    req = urllib.request.Request(url, None, headers)
    res = urllib.request.urlopen(req)
    auth_response = {
        "body": res.read(),
        "headers": res.info()
    }
    return auth_response

def get_partial_key(auth_response):
    authtoken = auth_response["headers"]["x-radiko-authtoken"]
    offset = int(auth_response["headers"]["x-radiko-keyoffset"])
    length = int(auth_response["headers"]["x-radiko-keylength"])
    partialkey = base64.b64encode(auth_key[offset:offset+length].encode())
    return partialkey, authtoken

def auth2(partialkey, auth_token):
    url = "https://radiko.jp/v2/api/auth2"
    headers = {
        "X-Radiko-AuthToken": auth_token,
        "X-Radiko-Partialkey": partialkey,
        "X-Radiko-User": "dummy_user",
        "X-Radiko-Device": "pc"
    }
    req = urllib.request.Request(url, None, headers)
    res = urllib.request.urlopen(req)
    area = res.read().decode()
    return area

def gen_temp_chunk_m3u8_url(url, auth_token):
    headers = {
        "X-Radiko-AuthToken": auth_token,
    }
    req = urllib.request.Request(url, None, headers)
    res = urllib.request.urlopen(req)
    body = res.read().decode()
    lines = re.findall('^https?://.+m3u8$', body, flags=re.MULTILINE)
    return lines[0]

def get_area_info(auth_token):
    url = "https://radiko.jp/v2/api/area"
    headers = {
        "X-Radiko-AuthToken": auth_token,
    }
    req = urllib.request.Request(url, None, headers)
    res = urllib.request.urlopen(req)
    area_info = res.read().decode()
    return area_info

def get_station_info_by_area(area_id):
    url = "http://radiko.jp/v3/station/region/full.xml"
    req = urllib.request.Request(url)
    res = urllib.request.urlopen(req)
    xml_data = res.read().decode()
    root = ET.fromstring(xml_data)

    stations = []
    for region in root.findall('stations'):
        for station in region.findall('station'):
            if station.find('area_id').text == area_id:
                station_id = station.find('id').text
                station_name = station.find('name').text
                stations.append((station_id, station_name))
    return stations

def parse_args():
    parser = argparse.ArgumentParser(description="Radiko listener")
    parser.add_argument("station", nargs='?', help="Station ID to listen to")
    parser.add_argument("--area", action="store_true", help="Show station list for the area")
    parser.add_argument("--area_id", help="Area ID to filter stations")
    return parser.parse_args()

def mock_station_list():
    # Mock function to simulate station list
    return ["STATION1", "STATION2", "STATION3"]

def main():
    res = auth1()
    partialkey, token = get_partial_key(res)
    area_info = auth2(partialkey, token)
    print(area_info)

    area_id = area_info.split(',')[0]

    args = parse_args()

    if args.area:
        if args.area_id:
            stations = get_station_info_by_area(args.area_id)
            print("Available stations in area", args.area_id, ":\n", "\n".join([f"{id} ({name})" for id, name in stations]))
        else:
            stations = get_station_info_by_area(area_id)
            print("Available stations in area", area_id, ":\n", "\n".join([f"{id} ({name})" for id, name in stations]))
    else:
        station = args.station
        if not station:
            print("Please provide a station ID or use --area to list available stations.")
            sys.exit(1)

        url = f"http://f-radiko.smartstream.ne.jp/{station}/_definst_/simul-stream.stream/playlist.m3u8"
        m3u8 = gen_temp_chunk_m3u8_url(url, token)
        print(token)
        print(m3u8)
        cmd = f"ffplay -nodisp -loglevel quiet -headers 'X-Radiko-Authtoken:{token}' -i '{m3u8}'"
        print(cmd)
        os.system(cmd)

if __name__ == "__main__":
    main()
