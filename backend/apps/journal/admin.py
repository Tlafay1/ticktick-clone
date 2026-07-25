from django.contrib import admin

from .models import JournalEntry, JournalMoment


class JournalMomentInline(admin.TabularInline):
    model = JournalMoment
    extra = 0


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ["date", "user", "mood", "updated_at"]
    inlines = [JournalMomentInline]
