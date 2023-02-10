import requests

BASE_URL = 'https://nominatim.openstreetmap.org/search'


class NominatimStatusCodeError(Exception):
    pass


def query(query_str, format='json', language='en-US'):
    params = {
        'q': query_str,
        'format': format
        }

    headers = {
        'Accept-Language': language
    }

    response = requests.get(BASE_URL, params=params, headers=headers)

    if response.status_code < 200 or response.status_code >= 300:
        raise NominatimStatusCodeError(f'Nominatim returned status code {response.status_code}')

    return response.json()
