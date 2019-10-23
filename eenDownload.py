# encoding: utf-8
__author__ = 'lianggao'
__date__ = '2019/10/5 1:47 PM'

from gevent import monkey;monkey.patch_all()
import os
import gevent
import requests
import json
import random
from gevent.pool import Pool

USER_EMAIL = "demo@een.com"
USER_PASS_WORD = "bettercloud"

AUTHENTICATE_REQUEST_URL = "https://login.eagleeyenetworks.com/g/aaa/authenticate"
AUTHORIZE_REQUEST_URL = "https://login.eagleeyenetworks.com/g/aaa/authorize"
BRIDGE_LIST_REQUEST_URL_PART = ".eagleeyenetworks.com/g/device/list"
GET_IMAGE_URL_PART = ".eagleeyenetworks.com/asset/asset/image.jpeg"
HTTP_REQUEST_COMMON_PART = "https://"

STORAGE_FILE_DIR = os.path.abspath(os.path.dirname(os.getcwd()) + os.path.sep + ".") + "/EEN/out/"

MAX_DOWNLOAD_FILE_NUM = 20
MAX_CONCURRENCY_WORKER_NUM = 5
finished = 0

session = requests.session()
gevent_pool = Pool(MAX_CONCURRENCY_WORKER_NUM)


def authenticate_request():
    """Step 1, Authenticate with username and password."""

    # Use username, password and API Key to send a POST request to
    # https://login.eagleeyenetworks.com/g/aaa/authenticate
    # to get the authenticate. Because this is a demo account,
    # does not need to bring the API Key.
    print(">>>> [Authenticate Request] start <<<")
    authenticate_data = json.dumps({
        "username": USER_EMAIL,
        "password": USER_PASS_WORD
    })
    authenticate_header = {
        "content-type": "application/json"
    }
    try:
        authenticate_response = session.request("POST", AUTHENTICATE_REQUEST_URL, data=authenticate_data,
                                                headers=authenticate_header)
    except Exception as e:
        print(">>>> [Authenticate Request] Exception: {}".format(e))
        return
    if authenticate_response.status_code != 200:
        print("{}, {}".format(authenticate_response.status_code, authenticate_response.text))
        raise Exception
    auth_token = json.loads(authenticate_response.text)['token']
    print(">>>> [Authenticate Request] Successfully get auth_token:\n {} \n".format(auth_token))
    authorize_request(auth_token)


def authorize_request(auth_token):
    """Step 2, Authorize with the token returned by Authenticate."""

    # Bring the auth_key, which is coming from step 1, to send a POST request to
    # https://login.eagleeyenetworks.com/g/aaa/authorize
    # to authorize the session.
    # Again, because of the demo account, does not need to bring API key.
    print(">>>> [Authorize Request] start <<<")
    authorize_data = json.dumps({
        "token": auth_token
    })
    authorize_header = {
        "content-type": "application/json"
    }
    try:
        authorize_response = session.request("POST", AUTHORIZE_REQUEST_URL, data=authorize_data, headers=authorize_header)
    except Exception as e:
        print(">>>> [Authorize Request] Exception:{}".format(e))
        return
    if authorize_response.status_code != 200:
        print("{}, {}".format(authorize_response.status_code, authorize_response.text))
        raise Exception
    auth_json = json.loads(authorize_response.text)
    auth_key = authorize_response.cookies['auth_key']
    print(">>>> [Authorize Request] Successfully get auth_key:\n {} \n".format(auth_key))
    subdomain = auth_json['active_brand_subdomain']
    get_camera_list(subdomain)


def get_camera_list(subdomain):
    """Step 3, Get available camera."""

    # Try to get bridge list by sending a GET request to
    # "https://[active_brand_subdomain].eagleeyenetworks.com/g/device/list"
    # with session cookies. The response's result is not all available for
    # using. It should be filtering by filter_camera_list() method.
    print(">>>> [GetListOfBridge Request] start <<<")
    camera_list_url = HTTP_REQUEST_COMMON_PART + subdomain + BRIDGE_LIST_REQUEST_URL_PART
    try:
        camera_list_response = session.request("GET", camera_list_url)
    except Exception as e:
        print(">>>> [Authorize Request] Exception: {}".format(e))
        return
    if camera_list_response.status_code != 200:
        print("{}, {}".format(camera_list_response.status_code, camera_list_response.text))
        raise Exception
    camera_list = filter_camera_list(json.loads(camera_list_response.text))
    check_camera_before_download(subdomain,camera_list)


def check_camera_before_download(subdomain, camera_list):
    """Step 4, check whether the camera is ready to download image before use GEvent downloading."""
    for camera_item in camera_list:
        if check_camera_available(subdomain, camera_item[1]):
            gevent_download(subdomain, camera_item[1])
            break


def gevent_download(subdomain, camera_id):
    """Step 5, use GEvent to download camera preview images."""

    # Use GEvent to download camera preview images.
    # Gevent.pool size is 5, which can make sure that the number of concurrency
    # worker greenlets is 5 too. All the download request are Asynchronous.
    # Here we should create greenlets more than 20 in case of any request failed. I choose 30.
    # It is fault tolerant.
    jobs = [gevent_pool.spawn(image_downloader, index, subdomain, camera_id) for index in range(30)]
    gevent.joinall(jobs)


def check_camera_available(subdoamin, camera_id):
    """Checking the camera is available to download images or not."""

    # Although we have filter_camera_list() method to filter and pick up the available
    # cameras，some cameras are still unavailable to download. It may be offline or have
    # some problems suddenly.
    # This method is just to 99% make sure that camera is able to be download. The left 1%
    # is that camera may just happened accident after we check it is fine.
    # Accident happens, who knows. We are doing our best to guarantee the download successfully.
    print(">>>> [Checking Camera] check cameraID: {} --start--<<<".format(camera_id))
    request_image_data = {
        "id": camera_id,
        "timestamp": "now",
        "asset_class": "pre"
    }
    try:
        checking_url = HTTP_REQUEST_COMMON_PART + subdoamin + GET_IMAGE_URL_PART
        checking_response = session.request("GET", checking_url, params=request_image_data, timeout=15)
        if checking_response.status_code == 200 \
                and 'content-type' in checking_response.headers._store.keys()\
                and checking_response.headers._store['content-type'][1].split('/')[0] == 'image':
            print(">>>> [Checking Camera] CameraID: {} is available to download. Start to download.\n".format(camera_id))
            return True
        else:
            print(">>>> [Checking Camera] CameraID: {} is not available to download preview images, continue checking...\n".format(camera_id))
            return False
    except Exception as e:
        print(">>>> [Checking Camera] CameraID: {} is not available to download preview images with exception: {} continue checking...\n".format(camera_id, e))
        return False


def image_downloader(index, subdoamin, camera_id):
    """Download Camera Image by cameraID."""

    # Download the preview Camera Images by specified Camera ID.
    # Storage the image in local disks.
    global finished
    # Using a global variable to control whether or not continue to download images.
    # It the number reach the MAX, then return.
    if finished >= MAX_DOWNLOAD_FILE_NUM:
        return
    print(">>>> [Image Downloader] download cameraID: {} index: {} --start--<<<, Finished: {}".format(camera_id, index, finished))
    request_image_data = {
        "id": camera_id,
        "timestamp": "now",
        "asset_class": "pre"
    }
    try:
        download_url = HTTP_REQUEST_COMMON_PART + subdoamin + GET_IMAGE_URL_PART
        download_response = session.request("GET", download_url, params=request_image_data, timeout=15)
    except Exception as e:
        print(">>>> [Image Downloader] Exception: {}".format(e))
    if download_response.status_code != 200:
        print(">>>> [Image Downloader FAILED] CameraID: {} index: {} download failed. Status Code: {} {}"
              .format(camera_id, index, download_response.status_code, download_response.text))
        return
    if 'content-type' in download_response.headers._store.keys():
        content_type_split_list = download_response.headers._store['content-type'][1].split('/')
        if content_type_split_list[0] == 'image':
            preview_filename = STORAGE_FILE_DIR + ('%02d' % index) + "-" + camera_id + "-" + \
                               download_response.headers._store['x-ee-timestamp'][1] + "." + content_type_split_list[1]
        try:
            with open(preview_filename, 'wb') as file:
                file.write(download_response.content)
            finished += 1
            print(">>>> [Image Downloader] Successfully storage {} iamge. index: {}. Finished: {}".format(camera_id, index, finished))
            if finished == MAX_DOWNLOAD_FILE_NUM:
                terminate()
        except Exception as e:
            print(">>>> [Image Downloader] Exception: {}".format(e))
    else:
        print(">>>> [Image Downloader] response is not an Image file.")


def filter_camera_list(data_list):
    """Filtering the camera list and picking out the available cameras."""

    # Trying to pick up available cameras.
    # Unavailable cameras situations: 1. 'Device Type' is not 'camera', which is not_camera_list;
    #                                 2. 'is_unsupported' value is NOT supported(1), which is unsupported_camera_list;
    #                                 3. 'Camera ID' value is None, which is no_camera_id_list.
    available_camera_list = list()
    not_camera_list = list()
    no_camera_id_list = list()
    unsupported_camera_list = list()
    for index, item in enumerate(data_list):
        # 'Device Type' is not 'camera', put item into not_camera_list
        if item[3] != 'camera':
            not_camera_list.append(item)
            continue
        # 'is_unsupported' is 1, put item into unsupported_camera_list
        if item[13] == 1:
            unsupported_camera_list.append(item)
            continue
        # 'Camera ID' value is None, put item into no_camera_id_list.
        if item[1] is None:
            no_camera_id_list.append(item)
            continue
        available_camera_list.append(item)
    print(">>>> [Filter Camera List] Available_camera_list, length is {}.".format(len(available_camera_list)))
    print(">>>> [Filter Camera List] Unsupported_camera_list, length is {}.".format(len(unsupported_camera_list)))
    print(">>>> [Filter Camera List] Not_camera_list, length is {}.".format(len(not_camera_list)))
    print(">>>> [Filter Camera List] No_camera_id_list, length is {}.\n".format(len(no_camera_id_list)))
    # Here using random.shuffle() to shuffle the list in place for pick a random camera download in next step.
    random.shuffle(available_camera_list)
    return available_camera_list


def terminate():
    print(">>>> [Terminate] <<<\n Download File Number: {}".format(finished))
    gevent_pool.kill()


def start_run():
    print(">>>> [Starting] <<<\n")
    authenticate_request()


if __name__ == '__main__':
    start_run()