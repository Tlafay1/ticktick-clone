from django.contrib import admin

from .models import Project, ProjectGroup, Section

admin.site.register(ProjectGroup)
admin.site.register(Project)
admin.site.register(Section)
