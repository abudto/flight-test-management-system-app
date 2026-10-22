from django.contrib import admin

# Register your models here.
from .models import Program, Aircraft

admin.site.register(Program)
admin.site.register(Aircraft)