package org.operix.rpc;

import org.sikuli.script.ObserveEvent;
import org.sikuli.script.ObserverCallBack;

/** Adapter for Oculix's concrete observer callback class. */
final class PythonObserverCallback extends ObserverCallBack {
    interface Handler { void invoke(String method, ObserveEvent event); }
    private final Handler handler;
    PythonObserverCallback(Handler handler) { this.handler = handler; }
    @Override public void appeared(ObserveEvent event) { handler.invoke("appeared", event); }
    @Override public void vanished(ObserveEvent event) { handler.invoke("vanished", event); }
    @Override public void changed(ObserveEvent event) { handler.invoke("changed", event); }
    @Override public void findfailed(ObserveEvent event) { handler.invoke("findfailed", event); }
    @Override public void missing(ObserveEvent event) { handler.invoke("missing", event); }
    @Override public void happened(ObserveEvent event) { handler.invoke("happened", event); }
}
