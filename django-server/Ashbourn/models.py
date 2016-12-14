import hashlib
import time

from django.core.validators import RegexValidator
#from django.db import models
from django.contrib.gis.db import models

# Create your models here.


class WorldBorder(models.Model):
    # Regular Django fields corresponding to the attributes in the
    # world borders shapefile.
    name = models.CharField(max_length=50)
    area = models.IntegerField()
    pop2005 = models.IntegerField('Population 2005')
    fips = models.CharField('FIPS Code', max_length=2)
    iso2 = models.CharField('2 Digit ISO', max_length=2)
    iso3 = models.CharField('3 Digit ISO', max_length=3)
    un = models.IntegerField('United Nations Code')
    region = models.IntegerField('Region Code')
    subregion = models.IntegerField('Sub-Region Code')
    lon = models.FloatField()
    lat = models.FloatField()

    # GeoDjango-specific: a geometry field (MultiPolygonField)
    mpoly = models.MultiPolygonField()

    # Returns the string representation of the model.
    def __str__(self):              # __unicode__ on Python 2
        return self.name

def gen_hash(id, length=None):
    if length is None:
        length = 10
    hash = hashlib.sha1()
    hash.update(str(str(id) + "~~~~~~" + str(time.time())).encode('utf-8'))
    return hash.hexdigest()[-length:]


class Location(models.Model):
    # id = models.PositiveIntegerField();
    name = models.CharField(max_length=50, default='')
    address = models.CharField(max_length=30)
    #geofence = models.CharField(max_length=80)
    lon = models.FloatField()
    lat = models.FloatField()
    description = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Person(models.Model):
    # id = models.PositiveIntegerField();
    watch_id = models.CharField(max_length=20)
    tag_id = models.CharField(max_length=20)
    name = models.CharField(max_length=50)
    location = models.ForeignKey('Location', null=True, blank=True, related_name='locations')
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
    owner = models.CharField(max_length=1, default='P')
    category = models.CharField(max_length=20, default='not specified')
    person = models.ForeignKey('Person', null=True, related_name='activities')
    location = models.ForeignKey('Location', null=True, blank=True)
    time = models.DateTimeField()
    activity_type = models.CharField(max_length=100)
    activity_data = models.TextField(default='', blank=True)

    def __str__(self):
        return "%s %s - %s" % (str(self.time), self.person.__str__(), self.activity_type)

    class Meta:
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'



