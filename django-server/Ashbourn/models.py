import hashlib
import time

from django.core.validators import RegexValidator
#from django.db import models
from django.contrib.gis.db import models
import math

# projection transformation for coords
def merc_x(lon):
  r_major=6378137.000
  return r_major*math.radians(lon)

def merc_y(lat):
  if lat>89.5:lat=89.5
  if lat<-89.5:lat=-89.5
  r_major=6378137.000
  r_minor=6356752.3142
  temp=r_minor/r_major
  eccent=math.sqrt(1-temp**2)
  phi=math.radians(lat)
  sinphi=math.sin(phi)
  con=eccent*sinphi
  com=eccent/2
  con=((1.0-con)/(1.0+con))**com
  ts=math.tan((math.pi/2-phi)/2)/con
  y=0-r_major*math.log(ts)
  return y

class Location(models.Model):
    # Regular Django fields corresponding to the attributes in the
    # world borders shapefile.
    name = models.CharField(max_length=50, default='')
    address = models.CharField(max_length=30)
    fence = models.MultiPolygonField()
    description = models.CharField(max_length=50)
    person = models.ForeignKey('Person',null=True, blank=True)
    # GeoDjango-specific: a geometry field (MultiPolygonField)

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
    tag_id = models.CharField(max_length=20)
    name = models.CharField(max_length=50)
    home = models.ForeignKey('Location', null=True, blank=True, related_name='home')
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    cell_number = models.CharField(validators=[phone_regex],  max_length=15)  # validators should be a list
    hash = models.CharField(max_length=10, null=True, blank=True, unique=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.hash = gen_hash(self.id)
        super(Person, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Relation(models.Model):
    relation_type = models.CharField(max_length=20)
    person_1 = models.ForeignKey('Person', related_name='relations')
    person_2 = models.ForeignKey('Person')

    def __str__(self):
        return "%s %s %s" % (self.person_1.__str__(), self.relation_type, self.person_2.__str__())


class Activity(models.Model):
    category = models.CharField(max_length=20, default='not specified')
    person = models.ForeignKey('Person', null=True, related_name='activities')
    time = models.DateTimeField()
    activity_type = models.CharField(max_length=100)
    call_duration = models.CharField(max_length=10,blank=True)
    to_from = models.CharField(max_length=20,blank=True)
    text = models.TextField(default='',blank = True)
    location = models.ForeignKey('Location', null=True, blank=True)
    actPoint = models.PointField(null=True)
    locLat = models.DecimalField(max_digits=10, decimal_places=2)
    locLon = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return "%s %s - %s" % (str(self.time), self.person.__str__(), self.activity_type)
    def save(self, *args, **kwargs):
        self.locLat =  merc_y(self.actPoint.y)
        self.locLon =  merc_x(self.actPoint.x)
        super(Activity, self).save(*args, **kwargs)  

    class Meta:
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'



