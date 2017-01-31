import hashlib
import time
import math
from django.core.validators import RegexValidator
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from multiselectfield import MultiSelectField
from pyproj import Proj, transform

class Location(models.Model):
    SOCIAL = 'Social'
    HEALTH = 'Health'
    HOME = 'Home'
    OTHER = 'Other'
    HARMFUL = 'Harmful'
    LOCATION_CATEGORIES = (
        (SOCIAL, 'Social'),
        (HEALTH, 'Health'),
        (HOME, 'Home'),
        (OTHER, 'Other(out of house tasks)'),
        (HARMFUL, 'Harmful/dangerous known place to be'),
    )
    name = models.CharField(max_length=100, default='', unique=True)
    person = models.ForeignKey('Person',null=True, blank=True)
    category = MultiSelectField(choices= LOCATION_CATEGORIES, default= OTHER, null=False)
    description = models.CharField(max_length=50)
    fence = models.MultiPolygonField(srid=3857)
    # GeoDjango-specific: a geometry field (MultiPolygonField)

    def update(self, *args, **kwargs):
        super(Location, self).save(*args, **kwargs)

    # Returns the string representation of the model.
    def __str__(self):              # __unicode__ on Python 2
        return self.name 

def gen_hash(id, length=None):
    if length is None:
        length = 10
    hash = hashlib.sha1()
    hash.update(str(str(id) + "~~~~~~" + str(time.time())).encode('utf-8'))
    return hash.hexdigest()[-length:]

class Person(models.Model):
    # id = models.PositiveIntegerField();
    watch_id = models.CharField(max_length=20)
    name = models.CharField(max_length=50)
    home = models.ForeignKey('Location', null=True, blank=True, related_name='home')
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    cell_number = models.CharField(validators=[phone_regex],  max_length=15, null=True, blank=True)  # validators should be a list
    hash = models.CharField(max_length=10, null=True, blank=True, unique=True)

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = gen_hash(self.id)

        super(Person, self).save(*args, **kwargs)
        # update location 
        if self.home:
            loc_home = Location.objects.filter(name=self.home.name)[0]
            if loc_home.person == None:
                loc_home.person = self
                loc_home.update()

    def __str__(self):
        return self.name


class Relation(models.Model):
    FAMILY = 'Family'
    FRIENDS = 'Friends'
    HEALTH = 'Health'
    NEGATIVE = 'Negative relationship or enemy'
    REL_TYPES = (
        (FAMILY, 'Family'),
        (FRIENDS, 'Friends'),
        (HEALTH, 'Health'),
        (NEGATIVE, 'Negative'),
    )
    relation_type = MultiSelectField(choices= REL_TYPES, default= FRIENDS)
    person_1 = models.ForeignKey('Person', related_name='relations')
    person_2 = models.ForeignKey('Person')

    def __str__(self):
        rel_string = '('
        for rel in self.relation_type:
            rel_string += str(rel) + ", "
        rel_string = rel_string[:-2] + ")"
        #print rel_string
        return "%s %s %s" % (self.person_1.__str__(), rel_string, self.person_2.__str__())


class Activity(models.Model):
    category = models.CharField(max_length=20, default='not specified')
    person = models.ForeignKey('Person', null=True, related_name='activities')
    time = models.DateTimeField()
    activity_type = models.CharField(max_length=100)
    call_duration = models.CharField(max_length=10,blank=True)
    to_from = models.CharField(max_length=20,blank=True)
    text = models.TextField(default='',blank = True)
    location = models.ForeignKey('Location', null=True, blank=True)
    adminPoint = models.PointField(null=True, srid=3857)
    locLat = models.DecimalField(max_digits=10, decimal_places=2)
    locLon = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return "%s %s - %s" % (str(self.time), self.person.__str__(), self.activity_type)

    def save(self, *args, **kwargs):
        
        if self.adminPoint:
            self.locLat =  self.adminPoint.y
            self.locLon =  self.adminPoint.x

        else:
            inProj = Proj(init='epsg:4326')
            outProj = Proj(init='epsg:3857')
            try:
                self.locLon,self.locLat = transform(inProj,outProj,float(self.locLon),float(self.locLat))
                pnt = Point(self.locLon, self.locLat, srid=3857)
                # see if in geofence
                if not self.location:
                    fence_loc = Location.objects.filter(fence__contains=pnt)
                    if fence_loc:
                        self.location = fence_loc[0]
            except Exception as e:
                print(e) # must be in correct coord system
        
        super(Activity, self).save(*args, **kwargs) 

    def update(self, *args, **kwargs):
        super(Activity, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'



