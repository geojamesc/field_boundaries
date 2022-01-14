# TODO use sentinelsat to download sentinel data for AOIs
from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt
from sentinelsat.exceptions import LTATriggered
import pprint
hub_username, hub_password = 'jcrone', 'kT8mzpsM3!'
s2_tilename = '30UWG'
api = SentinelAPI(hub_username, hub_password, 'https://scihub.copernicus.eu/dhus')
print("Searching for scenes for S2 tile {}...".format(s2_tilename))

s2_products = api.query(
    date=('20210601', '20210701'),
    platformname='Sentinel-2',
    processinglevel='Level-2A',
    cloudcoverpercentage=(0, 100),
    filename='*T{}*'.format(s2_tilename)
)

min_cc = 100
scene_w_min_cc = None

for p in s2_products:
    filename = s2_products[p]['filename']
    cloudcoverpercentage = s2_products[p]['cloudcoverpercentage']
    uuid = s2_products[p]['uuid']
    ondemand = s2_products[p]['ondemand']
    #print(filename, uuid, cloudcoverpercentage, ondemand)

    if cloudcoverpercentage < min_cc:
        min_cc = cloudcoverpercentage
        scene_w_min_cc = uuid


print('We want to download the scene with the min cc:', scene_w_min_cc)
try:
    p_info = api.download(scene_w_min_cc, '/home/james/geocrud')
except LTATriggered as ex:
    print('Exception raised:')
    print(ex)









