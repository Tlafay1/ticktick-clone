package com.ticktick.clone.widget;

import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Pont minimal app → widget : l'instantané est déjà écrit par Capacitor Preferences,
 * il ne reste qu'à demander aux widgets posés de se redessiner.
 */
@CapacitorPlugin(name = "WidgetBridge")
public class WidgetBridgePlugin extends Plugin {

    @PluginMethod
    public void refresh(PluginCall call) {
        TodayWidget.refreshAll(getContext());
        call.resolve();
    }
}
