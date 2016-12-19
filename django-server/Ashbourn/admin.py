#from django.contrib import admin
from django.contrib.gis import admin
from .models import Activity, Person, Relation, Location, GeoFence
# Register your models here.


class LocationAdmin(admin.ModelAdmin):
    model = Location


class PersonAdmin(admin.ModelAdmin):
    model = Person


class RelationAdmin(admin.ModelAdmin):
    model = Relation


class ActivityAdmin(admin.ModelAdmin):
    model = Activity

class GeoFenceAdmin(admin.OSMGeoAdmin):
    default_lon = -12636243
    default_lat = 7075850
    default_zoom = 12


admin.site.register(Location, LocationAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Relation, RelationAdmin)
admin.site.register(Activity, ActivityAdmin)
admin.site.register(GeoFence, GeoFenceAdmin)

