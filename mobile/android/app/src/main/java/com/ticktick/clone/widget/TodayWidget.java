package com.ticktick.clone.widget;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.view.View;
import android.widget.RemoteViews;

import com.ticktick.clone.MainActivity;
import com.ticktick.clone.R;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.Locale;

/**
 * Widget « Prochaine action » : le prochain créneau de la méthode et ce qu'il y a
 * à faire aujourd'hui, avec démarrer (10 min) et ajouter en un geste.
 *
 * Le widget ne parle jamais au serveur : il relit l'instantané que l'app écrit à
 * chaque synchro (Capacitor Preferences, src/lib/widget.ts). Les créneaux de la
 * semaine y sont déjà : le prochain se recalcule avec l'heure, même app fermée.
 */
public class TodayWidget extends AppWidgetProvider {

    /** Fichier de Capacitor Preferences (groupe par défaut). */
    static final String PREFS = "CapacitorStorage";
    static final String SNAPSHOT_KEY = "widget.snapshot";
    /** Action lue par l'app au retour au premier plan (MainActivity → Preferences). */
    public static final String ACTION_KEY = "widget.action";
    public static final String EXTRA_ACTION = "widget_action";

    // Mêmes règles que le serveur (méthode M36.4) : démarrable dès 1 h avant, raté 15 min après la fin.
    private static final long START_EARLY_MS = 60 * 60_000L;
    private static final long MISSED_GRACE_MS = 15 * 60_000L;

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        for (int id : ids) {
            manager.updateAppWidget(id, render(context, System.currentTimeMillis()));
        }
    }

    /** Redessine tous les widgets posés (appelé par l'app après chaque synchro). */
    public static void refreshAll(Context context) {
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        int[] ids = manager.getAppWidgetIds(new ComponentName(context, TodayWidget.class));
        long now = System.currentTimeMillis();
        for (int id : ids) {
            manager.updateAppWidget(id, render(context, now));
        }
    }

    static RemoteViews render(Context context, long now) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_today);
        JSONObject snapshot = readSnapshot(context);

        views.setOnClickPendingIntent(R.id.widget_root, open(context, null, 0));
        views.setOnClickPendingIntent(R.id.widget_add, open(context, "add", 1));

        if (snapshot == null) {
            views.setTextViewText(R.id.widget_header, "Aujourd'hui");
            views.setTextViewText(R.id.widget_slot, "Ouvre l'app pour charger ta journée");
            views.setViewVisibility(R.id.widget_start, View.GONE);
            views.setTextViewText(R.id.widget_tasks, "");
            return views;
        }

        applyTheme(views, snapshot.optString("theme", "auto"));
        views.setTextViewText(R.id.widget_header, header(snapshot));

        JSONObject slot = nextSlot(snapshot.optJSONArray("slots"), now);
        if (slot == null) {
            views.setTextViewText(R.id.widget_slot, "Aucun créneau à venir");
            views.setViewVisibility(R.id.widget_start, View.GONE);
        } else {
            long start = slot.optLong("start_ms");
            String title = slot.optString("title", "");
            String when = sameDay(start, now) ? format("HH:mm", start) : format("EEE HH:mm", start);
            String what = title.isEmpty() ? "prochaine action de ton objectif" : title;
            if ("buffer".equals(slot.optString("kind"))) what = "Rattrapage · " + what;
            views.setTextViewText(R.id.widget_slot, "🎯 " + when + " · " + what);
            boolean startable = sameDay(start, now) && now >= start - START_EARLY_MS;
            views.setViewVisibility(R.id.widget_start, startable ? View.VISIBLE : View.GONE);
            views.setOnClickPendingIntent(R.id.widget_start,
                    open(context, "start:" + slot.optLong("id"), 2));
        }

        views.setTextViewText(R.id.widget_tasks, tasks(snapshot.optJSONArray("tasks")));
        return views;
    }

    /**
     * Thème choisi dans l'app. « auto » : rien à forcer, les ressources values-night
     * suivent le mode sombre du téléphone (et changent avec lui, sans redessin).
     * « light » / « dark » : l'app a tranché, le widget suit l'app.
     */
    static void applyTheme(RemoteViews views, String theme) {
        if (!"light".equals(theme) && !"dark".equals(theme)) return;
        boolean dark = "dark".equals(theme);
        views.setInt(R.id.widget_root, "setBackgroundResource",
                dark ? R.drawable.widget_background_dark : R.drawable.widget_background_light);
        int text = dark ? 0xFFD6D6D6 : 0xFF202329;
        int secondary = dark ? 0xFF9A9A9A : 0xFF6B6F76;
        views.setTextColor(R.id.widget_header, text);
        views.setTextColor(R.id.widget_slot, text);
        views.setTextColor(R.id.widget_tasks, secondary);
    }

    private static JSONObject readSnapshot(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String raw = prefs.getString(SNAPSHOT_KEY, null);
        if (raw == null) return null;
        try {
            return new JSONObject(raw);
        } catch (Exception e) {
            return null;
        }
    }

    private static String header(JSONObject snapshot) {
        String color = snapshot.optString("color", "");
        String dot = "green".equals(color) ? "🟢 " : "orange".equals(color) ? "🟠 "
                : "red".equals(color) ? "🔴 " : "";
        return dot + "Aujourd'hui · " + snapshot.optInt("today_count") + "/" + snapshot.optInt("today_limit", 3);
    }

    /** Premier créneau encore à faire (prévu, ou raté mais pas encore clos). */
    static JSONObject nextSlot(JSONArray slots, long now) {
        if (slots == null) return null;
        for (int i = 0; i < slots.length(); i++) {
            JSONObject slot = slots.optJSONObject(i);
            if (slot != null && slot.optLong("end_ms") + MISSED_GRACE_MS > now) return slot;
        }
        return null;
    }

    private static String tasks(JSONArray titles) {
        if (titles == null || titles.length() == 0) return "Rien d'autre aujourd'hui.";
        StringBuilder text = new StringBuilder();
        for (int i = 0; i < titles.length(); i++) {
            if (i > 0) text.append('\n');
            text.append("• ").append(titles.optString(i));
        }
        return text.toString();
    }

    private static boolean sameDay(long a, long b) {
        Calendar ca = Calendar.getInstance();
        ca.setTimeInMillis(a);
        Calendar cb = Calendar.getInstance();
        cb.setTimeInMillis(b);
        return ca.get(Calendar.YEAR) == cb.get(Calendar.YEAR)
                && ca.get(Calendar.DAY_OF_YEAR) == cb.get(Calendar.DAY_OF_YEAR);
    }

    private static String format(String pattern, long millis) {
        return new SimpleDateFormat(pattern, Locale.FRANCE).format(new Date(millis));
    }

    /** Ouvre l'app, avec l'action du widget à exécuter (ou rien). */
    private static PendingIntent open(Context context, String action, int requestCode) {
        Intent intent = new Intent(context, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        if (action != null) intent.putExtra(EXTRA_ACTION, action);
        return PendingIntent.getActivity(context, requestCode, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }
}
