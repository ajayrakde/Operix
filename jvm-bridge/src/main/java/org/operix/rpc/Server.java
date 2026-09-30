package org.operix.rpc;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Line-delimited JSON-RPC server over stdin/stdout.
 *
 * Wire protocol — one JSON object per line in each direction.
 *
 * Request shapes:
 *   {"id":1, "class":"org.sikuli.script.Screen", "args":[]}
 *       -> construct an instance, returns {"id":1, "result":{"__ref":"o1"}}
 *
 *   {"id":2, "ref":"o1", "method":"click", "args":["btn.png"]}
 *       -> invoke method on a previously returned ref
 *
 *   {"id":3, "class":"org.sikuli.script.App", "method":"open",
 *    "args":["notepad"], "static":true}
 *       -> static method call
 *
 *   {"id":4, "ref":"o1", "release":true}
 *       -> drop the strong reference, allow GC
 *
 * Response shapes:
 *   {"id":N, "result": <json-value-or-{"__ref":"oK"}>}
 *   {"id":N, "error":  "stack trace string"}
 */
public final class Server {

    private final ObjectRegistry registry = new ObjectRegistry();
    private final Dispatcher dispatcher;
    private final PrintStream out;
    private final ConcurrentMap<String, CompletableFuture<JSONObject>> callbackReplies = new ConcurrentHashMap<>();
    private final ConcurrentMap<String, Object> callbackObjects = new ConcurrentHashMap<>();
    private final AtomicLong callbackIds = new AtomicLong();

    Server(PrintStream out) {
        this.out = out;
        this.dispatcher = new Dispatcher(registry, this::createCallback);
    }

    public static void main(String[] args) throws IOException {
        // Anything OculiX prints to stdout would corrupt the JSON-RPC stream.
        // Re-route stdout to stderr; keep the original stdout for our protocol.
        PrintStream rpcOut = System.out;
        System.setOut(System.err);

        OcrNativeBootstrap.initialize();
        new Server(rpcOut).run(System.in);
    }

    void run(java.io.InputStream in) throws IOException {
        ExecutorService requests = Executors.newCachedThreadPool();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.trim().isEmpty()) continue;
                try {
                    JSONObject message = new JSONObject(line);
                    if (message.has("callback_result")) {
                        CompletableFuture<JSONObject> waiter = callbackReplies.remove(message.getString("callback_result"));
                        if (waiter != null) waiter.complete(message);
                    } else {
                        final String request = line;
                        requests.submit(() -> handleLine(request));
                    }
                } catch (JSONException e) { writeError(JSONObject.NULL, "Invalid JSON: " + e.getMessage()); }
            }
        } finally {
            for (CompletableFuture<JSONObject> waiter : callbackReplies.values())
                waiter.completeExceptionally(new IOException("Python bridge disconnected"));
            requests.shutdown();
            try {
                if (!requests.awaitTermination(30, TimeUnit.SECONDS)) requests.shutdownNow();
            } catch (InterruptedException e) { Thread.currentThread().interrupt(); requests.shutdownNow(); }
        }
    }

    private Object invokeCallback(String id, String method, Object[] args, Class<?> resultType) throws Exception {
        String callId = "c" + callbackIds.incrementAndGet();
        CompletableFuture<JSONObject> reply = new CompletableFuture<>();
        callbackReplies.put(callId, reply);
        JSONArray values = new JSONArray();
        if (args != null) for (Object arg : args) values.put(dispatcher.encode(arg));
        writeLine(new JSONObject().put("callback", id).put("callback_id", callId).put("method", method).put("args", values));
        try {
            JSONObject result = reply.get(60, TimeUnit.SECONDS);
            if (result.has("error")) throw new IllegalStateException("Python callback: " + result.getString("error"));
            return resultType == void.class ? null : Dispatcher.coerceOne(resultType, dispatcher.decode(result.get("result")));
        } finally { callbackReplies.remove(callId); }
    }

    private Object createCallback(String id, String typeName) throws Exception {
        String key = id + ":" + typeName;
        Object existing = callbackObjects.get(key);
        if (existing != null) return existing;
        Object created;
        if (typeName.equals("org.sikuli.script.ObserverCallBack")) {
            created = new PythonObserverCallback((method, event) -> {
                try { invokeCallback(id, method, new Object[]{event}, void.class); }
                catch (Exception e) { throw new IllegalStateException(e); }
            });
        } else {
            Class<?> type = Class.forName(typeName);
            if (!type.isInterface()) throw new IllegalArgumentException("Callback type must be an interface or ObserverCallBack: " + typeName);
            created = Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[]{type}, (proxy, method, args) -> {
                if (method.getDeclaringClass() == Object.class) {
                    switch (method.getName()) {
                        case "hashCode": return System.identityHashCode(proxy);
                        case "equals": return proxy == args[0];
                        case "toString": return "Python callback " + id + " for " + typeName;
                        default: throw new UnsupportedOperationException(method.getName());
                    }
                }
                return invokeCallback(id, method.getName(), args, method.getReturnType());
            });
        }
        Object previous = callbackObjects.putIfAbsent(key, created);
        return previous == null ? created : previous;
    }

    private void handleLine(String line) {
        JSONObject request;
        Object id = JSONObject.NULL;
        try {
            request = new JSONObject(line);
            id = request.opt("id");
            JSONObject response = dispatcher.dispatch(request);
            response.put("id", id);
            writeLine(response);
        } catch (JSONException e) {
            writeError(id, "Invalid JSON: " + e.getMessage());
        } catch (Throwable t) {
            while (t instanceof InvocationTargetException && t.getCause() != null) {
                t = t.getCause();
            }
            writeError(id, t.toString());
        }
    }

    private void writeError(Object id, String message) {
        JSONObject err = new JSONObject();
        err.put("id", id == null ? JSONObject.NULL : id);
        err.put("error", message);
        writeLine(err);
    }

    private synchronized void writeLine(JSONObject obj) {
        out.println(obj.toString());
        out.flush();
    }

    static JSONArray emptyIfNull(JSONArray a) {
        return a == null ? new JSONArray() : a;
    }
}
