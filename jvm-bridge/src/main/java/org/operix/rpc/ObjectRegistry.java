package org.operix.rpc;

import java.util.IdentityHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Holds strong references to Java objects handed out to a remote client as
 * opaque {@code __ref} handles. The same Java instance always maps to the
 * same ref (identity-based interning) so chained calls like
 * {@code sb.append(x).append(y)} don't leak fresh refs on every step.
 *
 * Synchronized for concurrent requests and callback threads.
 */
final class ObjectRegistry {

    private final Map<String, Object> byId = new java.util.HashMap<>();
    private final IdentityHashMap<Object, String> byObj = new IdentityHashMap<>();
    private final AtomicLong counter = new AtomicLong();

    synchronized String register(Object obj) {
        String existing = byObj.get(obj);
        if (existing != null) return existing;
        String id = "o" + counter.incrementAndGet();
        byId.put(id, obj);
        byObj.put(obj, id);
        return id;
    }

    synchronized Object get(String id) {
        Object o = byId.get(id);
        if (o == null) {
            throw new IllegalArgumentException("Unknown ref: " + id);
        }
        return o;
    }

    synchronized void release(String id) {
        Object o = byId.remove(id);
        if (o != null) byObj.remove(o);
    }
}
