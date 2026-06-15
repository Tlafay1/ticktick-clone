from django.contrib import admin
from .models import Habit, HabitCheckIn, HabitReminder

admin.site.register(Habit)
admin.site.register(HabitCheckIn)
admin.site.register(HabitReminder)
