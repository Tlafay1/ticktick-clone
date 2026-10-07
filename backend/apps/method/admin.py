from django.contrib import admin

from .models import DayLog, MethodConfig, Slot, SlotOccurrence, WeeklyReview

admin.site.register(MethodConfig)
admin.site.register(Slot)
admin.site.register(SlotOccurrence)
admin.site.register(DayLog)
admin.site.register(WeeklyReview)
