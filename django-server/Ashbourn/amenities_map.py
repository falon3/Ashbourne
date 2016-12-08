#! /usr/bin/python

import libxml2
import libxslt

import urllib
import os

# Program to produce amenity layers for OpenLayers
# * Download data from OSM
# * Use XSLT to extract lat/lon pairs for each type of amenity
# * Build the poi.html framework for the layers

# Released for OSM under CC-by-SA licence

def main():
  
  libxml2.lineNumbersDefault(1)
  libxml2.substituteEntitiesDefault(1)
  
  # The extent of the data area to download from OSM
  min_lon=edit_me
  min_lat=edit_me
  max_lon=edit_me
  max_lat=edit_me
  
  # The initial zoom level for the POI html file.
  initial_zoom = 14

  # URL to fetch the OSM data from
  map_source_data_url="http://www.informationfreeway.org/api/0.6/map?bbox=%s,%s,%s,%s"\
  %(min_lon,min_lat,max_lon,max_lat)

  # Filename for OSM map data
  xml_filename = "map.osm"
  
  # Filename for XSLT to extract POIs
  xsl_filename = "amenities.xsl"

  # Filename for POI html file output
  poi_html_filename = "poi.html"

  # Layers we are going to extract (in a dict)
  # The key is the layer name, the value is a list of parameters:
  # 0,1: OSM key, value
  # 2: POI text output file name
  # 3: icon for this type of POI
  # 4,5: icon width,height (px)
  # 6,7: icon offset (x,y) (px)
  marker_layers={
    "Convenience stores":["shop", "convenience", "conbiniis.txt", "conbinii.png",32,37,-16,-37],
    "Hagwons":["amenity", "hagwon", "hagwons.txt", "hagwon.png",32,37,-16,-37],
    "Libraries":["amenity", "library", "libraries.txt", "library.png",32,37,-16,-37],
    "Post Offices":["amenity", "post_office", "postoffices.txt", "postoffice.png",32,37,-16,-37],
    "Schools":["amenity", "school", "schools.txt", "school.png",32,37,-16,-37],
    "Supermarkets":["shop", "supermarket", "supermarkets.txt", "supermarket.png",32,37,-16,-37],
     }

  # Calculate the centre of the map extent
  map_centre_lon = (min_lon + max_lon)/2 
  map_centre_lat = (min_lat + max_lat)/2 

  # Download the map.osm file from the net, if we don't already have one.
  if os.path.isfile(xml_filename):
    print "Not downloading map data.  '%s' already exists."%xml_filename
  else:
    print "Downloading OSM data."
    print "'%s' -> '%s'"%(map_source_data_url,xml_filename)
    urllib.urlretrieve(map_source_data_url,xml_filename)

  # Read the XML into memory.  We will use it many times.
  osmdoc = libxml2.parseFile(xml_filename)

  # Read the XSLT
  styledoc = libxml2.parseFile(xsl_filename)
  style = libxslt.parseStylesheetDoc(styledoc)

  # Extract POIs to layer text files
  for layer,tags in marker_layers.iteritems():
    print "Extracting '%s'..."%layer
    layer_filename = tags[2]
    result = style.applyStylesheet(osmdoc,\
    { "key":"'%s'"%tags[0], "value":"'%s'"%tags[1], "icon":"'%s'"%tags[3],\
    "width":"'%s'"%tags[4], "height":"'%s'"%tags[5],\
    "offsetx":"'%s'"%tags[6], "offsety":"'%s'"%tags[7]
    })
    style.saveResultToFilename(layer_filename, result, 0)

# Putting the HTML in the code is bad form, but it can be put somewhere else later
  poi_html_top='''<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <style type="text/css">
#map {
        width: 100%;
        height: 100%;
        border: 0px;
        padding: 0px;
        position: absolute;
     }
body {
        border: 0px;
        margin: 0px;
        padding: 0px;
        height: 100%;
     }
    </style>
    <script src="http://www.openlayers.org/api/OpenLayers.js"></script>
    <script src="http://www.openstreetmap.org/openlayers/OpenStreetMap.js"></script>
    <script type="text/javascript">
        <!--
        var map;
 
        function init(){
            map = new OpenLayers.Map('map',
                    { maxExtent: new OpenLayers.Bounds(-20037508.34,-20037508.34,20037508.34,20037508.34),
                      numZoomLevels: 19,
                      maxResolution: 156543.0399,
                      units: 'm',
                      projection: new OpenLayers.Projection("EPSG:900913"),
                      displayProjection: new OpenLayers.Projection("EPSG:4326")
                    });
 
            var layerMapnik = new OpenLayers.Layer.OSM.Mapnik("Mapnik");
 

            map.addLayers([layerMapnik,layerTah]);
'''

  poi_html_bottom=''' 
            map.addControl(new OpenLayers.Control.LayerSwitcher());
 
            var lonLat = new OpenLayers.LonLat(%s, %s).transform(map.displayProjection,  map.projection);
            if (!map.getCenter()) map.setCenter (lonLat, %s);
        }
        // -->
    </script>
  </head>
  <body onload="init()">
    <div id="map"></div>
  </body>
</html>'''%(map_centre_lon,map_centre_lat,initial_zoom)

  print "Writing '%s'..."%poi_html_filename
  f = open(poi_html_filename,"w")
  
  # Write out the POI html file.
  # This could be index.html if you like.
  f.write(poi_html_top)
  
  # Add the POI layers.  Make them all invisible initially.
  # Don't forget, dict entries are not ordered.  The list
  # of layers will appear in an inconsistent order.
  for layer,tags in marker_layers.iteritems():
    f.write ('''var pois = new OpenLayers.Layer.Text( "%s",
                    { location:"./%s",
                      projection: map.displayProjection,
                      visibility: 0
                    });
            map.addLayer(pois);'''%(layer,tags[2]))
  
  f.write(poi_html_bottom)
  f.close()

if __name__=="__main__":
  main()
