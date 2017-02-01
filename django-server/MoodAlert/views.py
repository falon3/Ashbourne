from .models import Activity, Person, Relation, Location
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.shortcuts import render_to_response, render, redirect
from django.template import loader
from django.contrib.gis.geos import GEOSGeometry, Point, WKTWriter, MultiPolygon
from itertools import chain
from vectorformats.Formats import Django, GeoJSON
from geojson import Feature, FeatureCollection
import dateutil.parser
import datetime
import geojson
import json
import collections

# handles GET request for /
@csrf_exempt
def get_home(request):
    return redirect("/website")
    

#helper function builds the object for a point location record    
def point_map_record(name, feat, point, activity, act_type):
    if act_type == "exit place":
        time = activity.time - datetime.timedelta(0,1)
    else:
        time = activity.time

    if activity.location:
        person = str(activity.location.person)
    else:
        person = str(activity.person)
    point_record = {
        'name' : name,
        'feature': feat, 
        'time': str(time), 
        'locLat': str(point.y), 
        'locLon': str(point.x), 
        'category': str(activity.category),
        'act_type': act_type,
        'person': person}
    return point_record

#helper function builds the object for a geofence record
def geofence_record(activity, fence, an_activity, time = '', person = ''):
    if an_activity:
        time = str(activity.time)
        person = str(activity.location.person)
        category = str([str(cat) for cat in activity.location.category])[1:-1]
        location = activity.location
        
    else:
        location = activity
        category = str([str(cat) for cat in location.category])[1:-1]
        person = str(location.person)

    record  = {
        'name':str(location.name), 
        'id': str(location.id),
        'feature': fence,
        'time': time,
        'description': str(location.description),
        'act_type': 'geo_fence',
        'category': category.replace("'",""),
        'person': person}
    return record

# handles GET request for the /map/ url
@csrf_exempt
def map_view(request):
    person_hash = request.GET.get('person_hash')
    person = Person.objects.get(hash=person_hash)
    
    feature_fences = collections.OrderedDict()
    wkt_w = WKTWriter()

    # get activity details from 'Location' activities for this person
    loc_activities = Activity.objects.filter(person=person,category="Location").order_by('time')
    j = 0    

    # for the table summary. Group all similar location activities in order
    processed = []
    currlocation = None
    currentplace = None  
    # build list of lists of separate journeys to then add to ordered dict of features for template to draw
    journeys = [[]] 
    for l in loc_activities:
        print l.time, l
        # current point
        pnt = Point(float(l.locLon),float(l.locLat), srid=3857)
        # see if in geofence but needs to be updated
        if not l.location:
            fence_loc = Location.objects.filter(fence__contains=pnt)
            if fence_loc:
                l.location = fence_loc[0]
                l.update()

        prior = {}
        prior['name'] = None
        prior['act_type'] = None
        if len(journeys[j]) > 0: 
            prior = journeys[j][-1]

        # if hit a known location add nearest boundary points too
        if l.location:

            # for the processed table groupings (append each place travelled to in order)
            if l.location != currlocation:
                processed.append({"time": str(l.time), "location": l.location, "person": l.person, "activity_type": str(l.activity_type)})
                currentplace = l
                currlocation = l.location

            # add the ENTRY boundary point then the location
            if str(l.location.name): # if has name then at known geofence 

                # went from location to location
                if prior['act_type'] == "geo_fence" and prior['name'] != l.location.name:
                    # use centroids as point to point reference
                    last_cnt =  GEOSGeometry(prior['feature']).centroid
                    wkt_feat = wkt_w.write(last_cnt)
                    to_add = point_map_record(str(l.location.name), wkt_feat, last_cnt, l, "exit place")
                    journeys[j].append(to_add)
                    # start next journey
                    journeys.append([]) 
                    j += 1
                    
                    # add entry point 
                    curr_cnt = l.location.fence.centroid
                    wkt_feat = curr_cnt.wkt
                    to_add = point_map_record(str(l.location.name), wkt_feat, curr_cnt, l, "enter location")
                    journeys[j].append(to_add)
                    
                # entered new location after a travel point
                # get entry point based on last recorded location
                elif prior['name'] and prior['name'] != l.location.name:
                     last_pnt = Point(float(prior['locLon']),float(prior['locLat']), srid=3857)           
                     boundary = l.location.fence.boundary
                     opt_dist = boundary.project(last_pnt)
                     # get point on boundary at that distance
                     entry = boundary.interpolate(opt_dist) 
                     wkt_feat = wkt_w.write(entry)
                     to_add = point_map_record(str(l.location.name), wkt_feat, entry, l, "enter location")
                     journeys[j].append(to_add)

                # add current location even if stayed in same location
                wkt_fence = wkt_w.write(l.location.fence)
                to_add = geofence_record(l, wkt_fence, True)
                journeys[j].append(to_add)
                
        # just travel point
        else:
            # for the table count travel as no location
            currlocation = None
            currentplace = None

            # may need exit point from last location to this current point
            if prior['act_type'] == "geo_fence": 
                boundary = GEOSGeometry(prior['feature']).boundary
                opt_dist = boundary.project(pnt)
                exitpnt = boundary.interpolate(opt_dist) 
                wkt_feat = wkt_w.write(exitpnt)
                to_add = point_map_record(str(prior['name']), wkt_feat, exitpnt, l, "exit place")
                journeys[j].append(to_add) 
                
                # start next journey after exit
                journeys.append([]) 
                j += 1
  
            wkt_feat = wkt_w.write(pnt)
            reg_point =  point_map_record("journey: " + str(j), wkt_feat, pnt, l, "moving")
            journeys[j].append(reg_point)

    # get additional known locations details for this person or their friends' homes
    all_friends = get_all_friends(person)
    fences = list(Location.objects.filter(person__hash=person_hash))
    for friend in all_friends:
        if friend.home:
            fences.append(friend.home)
    for f in fences:
        wkt_fence = wkt_w.write(f.fence)
        to_add = geofence_record(f, wkt_fence, False)
        feature_fences[str(f.name)] = [to_add]        

    # send all the data back to the template
    template = loader.get_template('MapView.html')   
    context = {}
    context['known_locations'] = sorted(feature_fences.iteritems())    
    context['title'] = "Activity Map for " + person.name
    context['point_collection'] = journeys #sorted(feature_points.items())
    # for item in context['point_collection']:
    #     for thing in item[1]:
    #         print thing['time']
    #     print "\n"
    context['selectperson'] = person
    context['location'] = 'all'
    context['time_from'] = 'all'
    context['time_to'] = 'now'
    context['query_result'] = processed   # for the table summary. all similar location activities grouped
    
    return JsonResponse(
        {'html': template.render(context)}
    )

# returns list of all person friends
def get_all_friends(person):
    friends = []
    result1 = Relation.objects.filter(person_1=person).all()
    result2 = Relation.objects.filter(person_2=person).all()
    result = list(chain(result1, result2))
    for relation in result:
        if not relation.person_1 == person:
            friends.append(relation.person_1)
        if not relation.person_2 == person:
            friends.append(relation.person_2)
    return friends

#handles GET for /calendar/
def calendar_view(request):
    person_hash = request.GET.get('person_hash')
    person = Person.objects.get(hash=person_hash)

    template = loader.get_template('calendarView.html')  
    context = {}
    context['title'] = "Activity Calendar for " + person.name

    activities = Activity.objects.filter(person=person,category="Location").order_by('time')
    intervals = [] # make a list of all time intervals spent at home
    current = []
    for act in activities:
        if len(current) > 1:
            print "what happened???", current
        if act.location:
            if act.location == person.home:
                if len(current)==0:
                    current.append(act.time) #interval entered home
                else:
                    continue # still at home
                    
            else:
                if len(current) > 0:
                    current.append(act.time) # count time left house as time entered this new place
                    intervals.append(current)
                    current = []
        else:
            if len(current) > 0:
                current.append(act.time) # time left house
                intervals.append(current)
                current = []

    data = {} # keys are the dates values will be total time for that day in milliseconds
    print intervals
    for period in intervals:
        pass
    # we want total time NOT at home so will do total milliseconds in a day - total for each
    # 86400000 milliseconds in one day
    for day in data.keys():
        data[day] = 86400000 - data[day]

    # TODO: get csv return to work and format it with time data
    # TODO: get second csv data to work also
    # field_names = ['Date', 'Time_Spent_Out']
    # response = HttpResponse(mimetype='text/csv')
    # response['Content-Disposition'] = 'attachment;filename=export.csv'
    # writer = csv.writer(response)
    # writer.writerow(field_names)
    # response.write(template.render(csv_data))
    # return render_to_response(template, {'context': context})

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
        {'html': template.render(context)}
    )


def show_relations_table(request):
    person_hash = request.GET.get('person_hash')
    result1 = Relation.objects.filter(person_1__hash=person_hash).all()
    result2 = Relation.objects.filter(person_2__hash=person_hash).all()
    result = list(chain(result1, result2))
    relations = []
    
    for rel in result:
        relation = {}
        rel_str = str(rel).split(' ') # get relation(s) as a nice tuple string
        rel_str = ' '.join(rel_str[1:-1])

        relation['person_1'] = str(rel.person_1)
        relation['person_2'] = str(rel.person_2)
        relation['relation'] = rel_str
        relations.append(relation)

    template = loader.get_template('relations_table.html')
    context = {
        'query_result': relations,
    }
    return JsonResponse(
        {'html': template.render(context)}
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
