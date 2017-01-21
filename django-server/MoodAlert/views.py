from .models import Activity, Person, Relation, Location
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.shortcuts import render_to_response, render, redirect
from django.template import loader
from django.contrib.gis.geos import GEOSGeometry, Point, WKTWriter, MultiPolygon
from shapely.geometry import MultiLineString
from itertools import chain
from vectorformats.Formats import Django, GeoJSON
from geojson import Feature, FeatureCollection
from shapely.geometry import mapping, shape
import dateutil.parser
import datetime
import geojson
import json
import collections
    
def point_map_record(num, feat, point, activity, category = None):
    if not category:
        category = str(activity.category)
    point_record = {
        'name' : 'Journey - ' + str(num),
        'feature': feat, 
        'time': str(activity.time), 
        'locLat': str(point.y), 
        'locLon': str(point.x), 
        'category': category, 
        'person': str(activity.person.name)}
    return point_record

@csrf_exempt
def map_view(request):
    person_hash = request.GET.get('person_hash')
    person = Person.objects.get(hash=person_hash)
    
    feature_points = collections.OrderedDict()
    feature_fences = collections.OrderedDict()
    wkt_w = WKTWriter()

    activity = 1
    # get activity details from 'Location' activities for this person
    loc_activities = Activity.objects.filter(person=person,category="Location").order_by('time')
    loc_list = list(loc_activities)
    locs_added = set()
    j = 0
    journeys = [[]] # build list of lists of separate journeys to then add to ordered dict of features for template to draw
    for l in loc_list:
        pnt = Point(float(l.locLon),float(l.locLat), srid=3857)
        # see if in geofence but needs to be updated
        if not l.location:
            fence_loc = Location.objects.filter(fence__contains=pnt)
            if fence_loc:
                l.location = fence_loc[0]
                l.update()

        # if hit a known location add nearest boundary points too
        if l.location:
            # add the location, then add the ENTRY boundary point
            if str(l.location.name):
                # may need exit point from last location 
                if len(journeys[j]) == 0 and  j > 0: 
                    print "FIRST journeys last place: ", journeys[j-1][-2]
                    print "\n\n\n\n\n\n\n\n"
                    last_place = journeys[j-1][-2]
                    boundary = GEOSGeometry(last_place['feature']).boundary
                    opt_dist = boundary.distance(pnt)
                    multiline = MultiLineString(boundary.coords)
                    # get point on multiline at that distance
                    exitpnt = multiline.interpolate(opt_dist) 
                    wkt_feat = exitpnt.wkt
                    to_add = point_map_record(j, wkt_feat, exitpnt, l, "exit place")
                    journeys[j].append(to_add) 

                # add current polygon location
                wkt_fence = wkt_w.write(l.location.fence)
                journeys[j].append({
                    'name':str(l.location.name), 
                    'id': str(l.location.id),
                    'feature': wkt_fence,
                    'time': str(l.time),
                    'address': str(l.location.address), 
                    'description': str(l.location.description), 
                    'person': str(l.person.name)})
                locs_added.add(str(l.location.name))

                # add optimal entry point used for this location
                # case 1: 1st activity recorded use center of location as entry
                if j == 0:
                    pnt = l.location.fence.centroid
                    wkt_feat = wkt_w.write(pnt)
                    to_add = point_map_record(j, wkt_feat, pnt, l, "center point")
                    journeys[j].append(to_add)

                # case 2: get entry point based on last recorded location
                else:
                    last = journeys[j][-2] # last point before location (could be exit)
                    last_pnt = Point(float(last['locLon']),float(last['locLat']), srid=3857)           
                    boundary = l.location.fence.boundary
                    opt_dist = boundary.distance(last_pnt)
                    multiline = MultiLineString(boundary.coords)
                    # get point on multiline at that distance
                    entry = multiline.interpolate(opt_dist) 
                    wkt_feat = entry.wkt
                    to_add = point_map_record(j, wkt_feat, entry, l, "enter location")
                    journeys[j].append(to_add)
    
            
            if len(journeys[j])>0:
                # hit a hit location so start next journey list
                journeys.append([]) 
                j += 1

        else:
            pnt = Point((float(l.locLon), float(l.locLat)), srid=3857)
            # may need exit point from last location to this current point
            if len(journeys[j]) == 0 and  j > 0: 
                print "journeys last place: ", journeys[j-1][-2]
                print "\n\n\n\n\n\n\n\n\n"
                last_place = journeys[j-1][-2]
                boundary = GEOSGeometry(last_place['feature']).boundary
                opt_dist = boundary.distance(pnt)
                multiline = MultiLineString(boundary.coords)
                # get point on multiline at that distance
                exitpnt = multiline.interpolate(opt_dist) 
                wkt_feat = exitpnt.wkt
                to_add = point_map_record(j, wkt_feat, exitpnt, l, "exit_place")
                journeys[j].append(to_add) 
  
            wkt_feat = wkt_w.write(pnt)
            reg_point =  point_map_record(j, wkt_feat, pnt, l)
            journeys[j].append(reg_point)
    
    for i in range(0,len(journeys)):
        if len(journeys[i]) > 0:
            feature_points["journey "+str(i)] = journeys[i]

    # get additional known locations details for this person
    fences = list(Location.objects.filter(person__hash=person_hash))
    for f in fences:
        wkt_fence = wkt_w.write(f.fence)
        feature_fences[str(f.name)] = [{
            'name' : str(f.name),
            'id': str(f.id),
            'feature': wkt_fence, 
            'address': str(f.address), 
            'description': str(f.description), 
            'person': str(f.person.name)}]

    template = loader.get_template('MapView.html')
    # send all the data back
    loc_activities = loc_activities.exclude(location__name=None).order_by('time')
    context = {}
    context['known_locations'] = sorted(feature_fences.iteritems())
    context['title'] = "Activity Map for " + person.name
    context['point_collection'] = sorted(feature_points.iteritems())
    context['selectperson'] = person
    context['location'] = 'all'
    context['time_from'] = 'all'
    context['time_to'] = 'now'
    context['query_result'] = loc_activities
    return JsonResponse(
        {'html': template.render(context, request)}
    )

# handles POST to /add_record/
# watch data from emails is added by callng this method
@csrf_exempt
def add_record_view(request):
    watch_id =  request.POST.get('watch_id', '')[1:] # strip the # sign
    activity_type = request.POST.get('activity_type', '')
    text = request.POST.get('text', '')
    call_duration = request.POST.get('call_duration','')
    to_from = request.POST.get('to_from','')
    person = Person.objects.get(watch_id=watch_id)
    time = dateutil.parser.parse(request.POST.get('time', ''))
    category = request.POST.get('category', '')
    location_name = request.POST.get('location', '')
    locLon = request.POST.get('locLon','')
    locLat = request.POST.get('locLat','')

    # if locLon, locLat intersect with a Location fence then add that to activity too
    if location_name != '':
        location = Location.objects.get(name=location_name)
        Activity.objects.create(time=time, activity_type=activity_type, text=text, person=person,
                                category=category, location=location, call_duration=call_duration,
                                to_from=to_from,locLon=locLon,locLat=locLat)
    else:
        Activity.objects.create(time=time, activity_type=activity_type, text=text, person=person,
                                category=category, call_duration=call_duration,
                                to_from=to_from,locLon=locLon,locLat=locLat)

    return JsonResponse({'message': 'record added! yoohoo!'})

@csrf_exempt
def get_locations(request):
    hash = request.POST['hash']
    person = Person.objects.get(hash=hash)
    loc_activities = Activity.objects.filter(person=person,category="Location")
    loc_list = list(loc_activities)
    str_result = ""
    for loc_act in loc_activities:
    	str_result += "time: " + str(loc_act.time) + ", data: " + loc_act.activity_data 
    return JsonResponse({'result':str_result})

@csrf_exempt
def get_locs_in_time(request):
    hash = request.POST['hash']
    person = Person.objects.get(hash=hash)
    time1 = dateutil.parser.parse(request.POST.get('time1', ''))
    time2 = dateutil.parser.parse(request.POST.get('time2', ''))
    activites = Activity.objects.filter(person=person,time__gte=time1,time__lte=time2,category="Location")
    str_result = ""
    for act in activites:
        str_result += str(act.time) + "---" + act.locLon + "," + act.locLat + "---"
    return JsonResponse({'result':str_result})
    
@csrf_exempt
def get_calls_in_time(request):
    hash = request.POST['hash']
    person = Person.objects.get(hash=hash)
    time1 = dateutil.parser.parse(request.POST.get('time1', ''))
    time2 = dateutil.parser.parse(request.POST.get('time2', ''))
    activites = Activity.objects.filter(person=person,time__gte=time1,time__lte=time2,category="Phone-Call")
    str_result = ""
    for act in activites:
        str_result += "time: " + str(act.time) + " type: " + str(act.activity_type) + "to_from: " + str(act.to_from) + " duration: " +  act.call_duration
    return JsonResponse({'result':str_result})

@csrf_exempt
def get_sms_in_time(request):
    hash = request.POST['hash']
    person = Person.objects.get(hash=hash)
    time1 = dateutil.parser.parse(request.POST.get('time1', ''))
    time2 = dateutil.parser.parse(request.POST.get('time2', ''))
    activites = Activity.objects.filter(person=person,time__gte=time1,time__lte=time2,category="Sms")
    str_result = ""
    for act in activites:
        str_result += "time: " + str(act.time) + " type: " + str(act.activity_type) + "to_from: " + str(act.to_from) + " text: " + str(act.text) 
    return JsonResponse({'result':str_result})

@csrf_exempt
def get_all_activities(request):
    hash = request.Post['hash']
    person = Person.objects.get(hash=hash)
    all_activities = Activity.objects.filter(person=person)
    act_list = list(all_activities)
    str_result = ""
    for act in all_activities:
        str_result += "time: " + str(act.time) + " category: " + act.category \
        + " location: " + str(act.location) + " type: " + str(act.activity_type) \
        + " text: " + str(act.text) 
    return JsonResponse({'result':str_result})

def test_get_info(request):
    return JsonResponse({'message': 'Im alive!! Im working :D'})


def show_person_table(request):
    query_result = Person.objects.all()
    template = loader.get_template('persons_table.html')
    context = {
        'query_result': query_result,
    }
    return JsonResponse(
        {'html': template.render(context, request)}
    )


def show_relations_table(request):
    person_hash = request.GET.get('person_hash')
    result1 = Relation.objects.filter(person_1__hash=person_hash).all()
    result2 = Relation.objects.filter(person_2__hash=person_hash).all()
    result = list(chain(result1, result2))

    template = loader.get_template('relations_table.html')
    context = {
        'query_result': result,
    }
    return JsonResponse(
        {'html': template.render(context, request)}
    )


def show_report_home(request):
    persons = Person.objects.all()
    locations = Location.objects.all()

    template = loader.get_template('report_home.html')
    context = {
        'persons': persons,
        'locations': locations,
    }

    if request.method == "POST":
        person_hash = request.POST.get('person', '')
        result = Activity.objects.all()
        context['selectperson'] = 'all'
        context['location'] = 'all'

        if person_hash != "all":
            result = Activity.objects.filter(person__hash=person_hash).all().order_by('time')
            context['selectperson'] = Person.objects.filter(hash=person_hash).first()

        location = request.POST.get('location', '')
        if location != "all":
            result = result.filter(location__name=location).all().order_by('time')
            context['location'] = location

        if not request.POST.get('time-from'):
            # default get 3 year range
            from_time = datetime.datetime.now() - datetime.timedelta(days=1096)
        else:
            from_time = dateutil.parser.parse(request.POST.get('time-from', ''))

        if not request.POST.get('time-to'):
            to_time = datetime.datetime.now()
        else:
            to_time = dateutil.parser.parse(request.POST.get('time-to', ''))

        result = result.filter(time__gte=from_time, time__lte=to_time).all().order_by('time')

        context['query_result'] = result
        context['time_from'] = from_time
        context['time_to'] = to_time

    return HttpResponse(template.render(context, request))
