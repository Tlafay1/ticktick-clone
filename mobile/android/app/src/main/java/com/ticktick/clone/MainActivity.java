package com.ticktick.clone;

import android.content.Intent;
import android.os.Bundle;

import com.getcapacitor.BridgeActivity;
import com.ticktick.clone.widget.TodayWidget;
import com.ticktick.clone.widget.WidgetBridgePlugin;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(WidgetBridgePlugin.class);
        super.onCreate(savedInstanceState);
        rememberWidgetAction(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        rememberWidgetAction(intent);
    }

    /**
     * Un tap sur « ▶ 10 min » ou « + » du widget ouvre l'app avec une action : on la
     * dépose dans Preferences, que l'app relit au retour au premier plan.
     */
    private void rememberWidgetAction(Intent intent) {
        if (intent == null) return;
        String action = intent.getStringExtra(TodayWidget.EXTRA_ACTION);
        if (action == null) return;
        getSharedPreferences("CapacitorStorage", MODE_PRIVATE).edit()
                .putString(TodayWidget.ACTION_KEY, action).apply();
        intent.removeExtra(TodayWidget.EXTRA_ACTION);
    }
}
