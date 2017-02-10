
import httplib
import json
import urllib

#for manual test watch location data for watch ID #3

def run_tests():
    data_base = { "category":"Location", 
                  "watch_id":"#3"}

    time = ["2017-01-18 21:47:12", "2017-01-18 21:48:12", "2017-01-18 21:49:12", "2017-01-18 21:50:12", "2017-01-18 21:51:12", 
            "2017-01-18 21:52:12", "2017-01-18 21:53:12", "2017-01-18 21:54:12", "2017-01-18 21:55:12", "2017-01-18 21:56:12"]

    locs = [("-113.51129210999295","53.5202598572" ), ("-113.51137257627013", "53.520247208209966"), ("-113.51139939835655","53.5202248827258"), 
            ("-113.51146377136928","53.520247208209966"), ("-113.51151205113558","53.52020255723042"), ("-113.51150132229564", "53.520094118940094"),
            ("-113.51154423764648","53.52006222527275" ), ("-113.5116676192565","53.52005265716754" ), ("-113.5117695432046","53.52005265716754" ), 
            ("-113.5119519334119","53.52005903590458" )]

    # -113.51139939835655,lat=53.5202248827258
    # lon=-113.51146377136928,lat=53.520247208209966
    # lon=-113.51151205113558,lat=53.52020255723042
    # lon=-113.51150132229564,lat=53.520094118940094
    # lon=-113.51154423764648,lat=53.52006222527275
    # lon=-113.5116676192565,lat=53.52005265716754
    # lon=-113.5117695432046,lat=53.52005265716754
    # lon=-113.5119519334119,lat=53.52005903590458
    for i in range(len(time)):
        data = data_base
        data["time"] = time[0]
        data["activity_type"] = "watch location " + str(i)
        data["locLat"] = locs[i][1]
        data["locLon"] = locs[i][0]
        data = urllib.urlencode(data)
        send_request(data)

def send_request(params):
    host = "127.0.0.1"
    port=5000
    url="/add_record/"
    headers = {"content-type" : "application/x-www-form-urlencoded"}
    conn = httplib.HTTPConnection(host,port)
    conn.request("POST",url, params, headers)

    response = conn.getresponse()
    resp = response.read()
    print resp

run_tests()
