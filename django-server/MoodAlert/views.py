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
import csv
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
        'name' : str(name),
        'feature': str(feat), 
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
        time = activity.time
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
        'feature': str(fence),
        'time': str(time),
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
    
    wkt_w = WKTWriter()

    # get activity details from 'Location' activities for this person
    loc_activities = Activity.objects.filter(person__hash=person_hash,category="Location").order_by('time')
    j = 0    

    # for the table summary. Group all similar location activities in order
    processed = []
    currlocation = None
    currentplace = None  
    
    journeys = [[]] # list of lists of separate journey dicts to then add to ordered dict of features for template to draw
    feature_fences = [] # list of lists of locations to add
    for l in loc_activities:
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
    
    # if at end and never left current place add last recroded point in location as 'exit'
    if len(journeys)>0:
        last_entry = journeys[-1][-1]
        if last_entry['act_type'] == 'geo_fence':
            last_cnt =  GEOSGeometry(last_entry['feature']).centroid
            wkt_feat = wkt_w.write(last_cnt)
            to_add = point_map_record(last_entry['name'], wkt_feat, last_cnt, l, "exit place")
            journeys[-1].append(to_add)

    # get additional known locations details for this person or their friends' homes
    all_friends = get_all_relation_people(person)
    fences = list(Location.objects.filter(person__hash=person_hash))
    for friend in all_friends:
        if friend.home:
            fences.append(friend.home)
    for f in fences:
        wkt_fence = wkt_w.write(f.fence)
        to_add = geofence_record(f, wkt_fence, False)
        feature_fences.append([to_add])    

    # send all the data back to the template
    template = loader.get_template('MapView.html')   
    context = {}
    context['known_locations'] = feature_fences  
    context['title'] = "Activity Map for " + person.name
    context['point_collection'] = journeys
    context['selectperson'] = person
    context['location'] = 'all'
    context['time_from'] = ''
    context['time_to'] = ''
    context['query_result'] = processed   # for the table summary. all similar location activities grouped
    return JsonResponse(
        {'html': template.render(context)}
    )

# returns list of all person friends
def get_all_relation_people(person):
    friends = []
    result = Relation.objects.filter(person_1=person) | Relation.objects.filter(person_2=person)
    for relation in result:
        if not relation.person_1 == person:
            friends.append(relation.person_1)
        if not relation.person_2 == person:
            friends.append(relation.person_2)
    return friends

# returns list of all person friends
def get_friends_fam(person):
    friends = []
    result1 = Relation.objects.filter(person_1=person, relation_type__contains='Friends').all() | Relation.objects.filter(person_1=person, relation_type__contains='Family').all()
    result2 = Relation.objects.filter(person_2=person, relation_type__contains='Friends').all() | Relation.objects.filter(person_2=person, relation_type__contains='Family').all()
    result = list(chain(result1, result2))
    for relation in result:
        if (not relation.person_1 == person):
            friends.append(relation.person_1)
        if (not relation.person_2 == person) and (relation.person_2 not in friends):
            friends.append(relation.person_2)
    return friends

# handles GET for /circles/
def circles_view(request):
    person_hash = request.GET.get('person_hash')
    person = Person.objects.get(hash=person_hash)

    template = loader.get_template('circlesView.html')  
    context = {}
    context['title'] = "Social Circles for " + person.name
    context['person'] = person

    #get_social_circles(request, person_hash)
    return JsonResponse(
        {'html': template.render(context, request)}
    )

# handles ajax request for /circles/person_hash/
def get_social_circles(request, person_hash):
    rel_dict = collections.defaultdict(list)
    rel_dict["Family"] = []
    rel_dict["Friends"] = []
    rel_dict["Health"] = []
    rel_dict["Negative"] = []
    person = Person.objects.get(hash=person_hash)
    activities = list(Activity.objects.filter(person__hash=person_hash,category="Location").order_by('time'))
    relations = Relation.objects.filter(person_1__hash=person_hash).all() | Relation.objects.filter(person_2__hash=person_hash).all()

    l1 = [rel.person_1 for rel in relations if not rel.person_1 == person]
    l2 = [rel.person_2 for rel in relations if not rel.person_2 == person and rel.person_2 not in l1]
    peeps_list = list(chain(l1,l2))                 
    
    intervals = collections.defaultdict(list) # make a list of all time interval lists spent with each person(person is key)
    for peep in peeps_list:
        intervals[str(peep.name)] = []
    
    current = []
    curr_peep = None
    for act in activities:
        if act.location:  
            if act.location.person in peeps_list:
                if len(current)==0 or (len(current)==1 and act == activities[-1]): # also add last one
                    current.append(act.time) #interval entered social location
                    curr_peep = act.location.person
                else:
                    continue # still socializing
                
            else:
                if len(current) > 0:
                    current.append(act.time) # count time left social place as time entered this new non social place
                    intervals[str(curr_peep.name)].append(current)
                    current = []
        else:
            if len(current) > 0:
                current.append(act.time) # time left last person's place
                intervals[str(curr_peep.name)].append(current)
                current = []

    if len(current)>1: # if missed one end point
        intervals[str(curr_peep.name)].append(current)
    
    person_times = {} # dict of dicts person with a dict of time for each day    
    for person_name in intervals.keys(): #each list for each person
        each_data = {} # keys are the people names, with list of dates values will be total time for that day 
        calculate_timedata(each_data, intervals[person_name])
        # we want total time socializing each day in seconds
        data_json = { str(key):value for key,value in each_data.items() } # all keys need to be strings for the json
        for day in data_json.keys():
            data_json[day] = data_json[day].seconds
        person_times[person_name] = data_json
        
    for rel in relations:
        if not rel.person_1 == person:
            add = rel.person_1
        else:
            add = rel.person_2
        for t in rel.relation_type:
            if {str(add.name): person_times[str(add.name)]} not in rel_dict[str(t)]:
                rel_dict[str(t)].append({str(add.name): person_times[str(add.name)]})

    return HttpResponse(json.dumps(rel_dict), content_type = "application/json")

#handles GET for /calendar/
def calendar_view(request):
    person_hash = request.GET.get('person_hash')
    person = Person.objects.get(hash=person_hash)

    template = loader.get_template('calendarView.html')  
    context = {}
    context['title'] = "Activity Calendar for " + person.name
    context['person'] = person

    return JsonResponse(
        {'html': template.render(context, request)}
    )

#handles ajax request for calendar data to /socialcdata/person_hash/
def social_cdata(request, person_hash):
    person = Person.objects.get(hash=person_hash)
    activities = list(Activity.objects.filter(person=person,category="Location").order_by('time'))
    friends = get_friends_fam(person)

    #for peop in known_people:
    #    pass
    intervals = [] # make a list of all time intervals spent at home
    current = []

    for act in activities:
        if act.location:
            categories = [str(cat) for cat in act.location.category]
            if "Social" in categories or act.location.person in friends:
                if len(current)==0 or (len(current)==1 and act == activities[-1]): # also add last one
                    current.append(act.time) #interval entered social location
                else:
                    continue # still socializing
                
            else:
                if len(current) > 0:
                    current.append(act.time) # count time left social place as time entered this new place
                    intervals.append(current)
                    current = []
        else:
            if len(current) > 0:
                current.append(act.time) # time left social place
                intervals.append(current)
                current = []

    if len(current)>1: # if missed one end point
        intervals.append(current)

    data = {} # keys are the dates values will be total time for that day 
    calculate_timedata(data, intervals)

    # we want total time socializing each day in seconds
    for day in data.keys():
        data[day] = data[day].seconds
    return send_csv_data(data)

#handles ajax request for calendar data to /movecdata/person_hash/
def move_cdata(request, person_hash):
    person = Person.objects.get(hash=person_hash)
    activities = list(Activity.objects.filter(person=person,category="Location").order_by('time'))
    intervals = [] # make a list of all time intervals spent at home
    current = []
    for act in activities:
        if act.location:
            if act.location == person.home:
                if len(current)==0 or (len(current)==1 and act == activities[-1]):
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
 
    if len(current)>1:
        intervals.append(current)
    data = {} # keys are the dates values will be total time for that day in milliseconds
    calculate_timedata(data, intervals)
    # we want total time NOT at home so will do total in a day - total for each
    for day in data.keys():
        data[day] = (datetime.timedelta(1) - data[day]).seconds
        #if data[day] == 0: # don't send data for nothing in a day
        #    data.pop(day)
    return send_csv_data(data)

# helper function to send csv data back from ajax request    
def send_csv_data(data):
    field_names = ['Date', 'Time_Spent']
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment;filename=export.csv'
    writer = csv.writer(response)
    writer.writerow(field_names)
    for entry in data.keys():
        writer.writerow([entry, data[entry]])
    return response
    
# helper function gets time stats puts them in given dict with dates as keys
def calculate_timedata(data_dict, interval_list): 
    if not interval_list:
        return
    for period in interval_list:
        if period[0].date() != period[1].date(): # interval goes overnight so add one for each day
            next_start = datetime.datetime(period[0].year, period[0].month, period[0].day) + datetime.timedelta(1)
            to_add = next_start - period[0] # time from current day

            if period[0].date() not in data_dict.keys():
                data_dict[period[0].date()]= to_add
            else:
                data_dict[period[0].date()]+= to_add
            period[0] = next_start # now start at next day til end
            sublist = []
            sublist.append(period)
            calculate_timedata(data_dict, sublist)

        else:
            to_add = period[1]-period[0]
            if period[0].date() not in data_dict.keys():
                data_dict[period[0].date()]= to_add
            else:
                data_dict[period[0].date()]+= to_add
    return

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
