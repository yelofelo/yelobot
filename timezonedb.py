import requests


BASE_URL = 'http://api.timezonedb.com/v2.1/get-time-zone'


class TimezoneDBStatusCodeError(Exception):
    pass


def query_lat_long(key, lat, long):
    params = {
        'key': key,
        'by': 'position',
        'lat': lat,
        'lng': long,
        'format': 'json'
    }

    return _request(params)

def query_zone(key, zone):
    params = {
        'key': key,
        'by': 'zone',
        'zone': zone,
        'format': 'json'
    }

    return _request(params)


def _request(params):
    response = requests.get(BASE_URL, params=params)

    if response.status_code < 200 or response.status_code >= 300:
        try:
            errormsg = response.json()['message']
        except:
            errormsg = None

        error_string = f'Status code {response.status_code} '
        if errormsg:
            error_string += f'Error message: {errormsg}'

        raise TimezoneDBStatusCodeError(error_string)

    return response.json()

    