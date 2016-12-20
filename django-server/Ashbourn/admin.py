#from django.contrib import admin
from django.contrib.gis import admin
from .models import Activity, Person, Relation, Location
# Register your models here.


class PersonAdmin(admin.ModelAdmin):
    model = Person


class RelationAdmin(admin.ModelAdmin):
    model = Relation


class ActivityAdmin(admin.ModelAdmin):
    model = Activity

class LocationAdmin(admin.OSMGeoAdmin):
    default_lon = -12636243
    default_lat = 7075850
    default_zoom = 12


admin.site.register(Person, PersonAdmin)
admin.site.register(Relation, RelationAdmin)
admin.site.register(Activity, ActivityAdmin)
admin.site.register(Location, LocationAdmin)

