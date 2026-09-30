package org.operix.rpc;

import org.json.JSONArray;
import org.json.JSONObject;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.lang.reflect.Array;
import java.lang.reflect.Executable;
import java.lang.reflect.Modifier;
import java.util.*;

/**
 * Routes a single JSON-RPC request to a constructor / static method /
 * instance method via reflection, then encodes the return value back to
 * JSON.
 *
 * Exact signatures from generated wrappers are preferred; generic calls use
 * type-aware overload selection, array/collection conversion and varargs.
 */
final class Dispatcher {

    private final ObjectRegistry registry;

    private final CallbackFactory callbacks;

    Dispatcher(ObjectRegistry registry) { this(registry, null); }
    Dispatcher(ObjectRegistry registry, CallbackFactory callbacks) {
        this.registry = registry;
        this.callbacks = callbacks;
    }
    interface CallbackFactory { Object create(String id, String type) throws Exception; }

    JSONObject dispatch(JSONObject req) throws Exception {
        if (req.has("resolve")) return new JSONObject().put("result", resolveOverload(req));
        // Release flow: drop a ref, no return value.
        if (req.optBoolean("release", false)) {
            registry.release(req.getString("ref"));
            return new JSONObject().put("result", JSONObject.NULL);
        }

        if (req.has("field")) {
            Object target = req.has("ref") ? registry.get(req.getString("ref")) : null;
            Class<?> owner = target != null ? target.getClass() : Class.forName(req.getString("class"));
            java.lang.reflect.Field field = owner.getField(req.getString("field"));
            if (target == null && !Modifier.isStatic(field.getModifiers())) throw new IllegalArgumentException("Instance field needs ref");
            if (req.has("value")) {
                field.set(target, coerceOne(field.getType(), decode(req.get("value"))));
                return new JSONObject().put("result", JSONObject.NULL);
            }
            return new JSONObject().put("result", encode(field.get(target)));
        }
        String methodName = req.optString("method", null);
        Class<?>[] exact = req.has("parameter_types") ? parameterTypes(req.getJSONArray("parameter_types")) : null;
        JSONArray jsonArgs = Server.emptyIfNull(req.optJSONArray("args"));
        Object[] args = decodeArgs(jsonArgs);

        Object result;

        if (req.has("ref")) {
            // Instance method call
            Object target = registry.get(req.getString("ref"));
            Method m = exact == null ? findMethod(target.getClass(), methodName, args.length, args, false)
                    : target.getClass().getMethod(methodName, exact);
            m = accessibleMethod(target, m);
            if (target instanceof java.lang.reflect.Field
                    && "set".equals(methodName) && args.length == 2) {
                // Field.set(obj, value): its (Object, Object) signature hides the
                // field's real type, so coerce(m, args) can't widen the value and
                // the JDK's strict Field.set rejects e.g. a Double for a float field
                // (Settings.MoveMouseDelay / WaitScanRate / ObserveScanRate). Coerce
                // against the field's ACTUAL type instead.
                java.lang.reflect.Field f = (java.lang.reflect.Field) target;
                args[1] = coerceOne(f.getType(), args[1]);
                result = m.invoke(target, args);
            } else {
                result = m.invoke(target, adapt(m, args));
            }
        } else if (req.has("class")) {
            String className = req.getString("class");
            Class<?> klass = Class.forName(className);
            if (methodName == null) {
                // Constructor call
                Constructor<?> c = exact == null ? findConstructor(klass, args.length, args) : klass.getConstructor(exact);
                result = c.newInstance(adapt(c, args));
            } else {
                // Static method call
                Method m = exact == null ? findMethod(klass, methodName, args.length, args, true) : klass.getMethod(methodName, exact);
                if (!Modifier.isStatic(m.getModifiers())) throw new IllegalArgumentException("Method is not static: " + m);
                result = m.invoke(null, adapt(m, args));
            }
        } else {
            throw new IllegalArgumentException("Request needs either 'ref' or 'class'");
        }

        return new JSONObject().put("result", encode(result));
    }

    /** Resolve generated candidates using the actual JVM type graph. */
    private int resolveOverload(JSONObject req) throws Exception {
        Class<?> owner = Class.forName(req.getString("class"));
        String name = req.getString("resolve");
        JSONArray candidates = req.getJSONArray("candidates");
        List<Integer> best = new ArrayList<>();
        List<Class<?>[]> signatures = new ArrayList<>();
        int bestScore = -1;
        for (int i = 0; i < candidates.length(); i++) {
            JSONObject candidate = candidates.getJSONObject(i);
            Class<?>[] types = parameterTypes(candidate.getJSONArray("parameter_types"));
            signatures.add(types);
            Executable member = name.equals("<init>") ? owner.getConstructor(types) : owner.getMethod(name, types);
            int score = executableScore(member, decodeArgs(candidate.getJSONArray("args")));
            if (score < 0) continue;
            if (score > bestScore) { best.clear(); bestScore = score; }
            if (score == bestScore) best.add(i);
        }
        if (best.isEmpty()) throw new IllegalArgumentException("No compatible Java overload for " + owner.getName() + "." + name);
        if (best.size() == 1) return best.get(0);
        for (int index : best) {
            boolean mostSpecific = true;
            for (int other : best) {
                Class<?>[] a = signatures.get(index), b = signatures.get(other);
                if (a.length != b.length) { mostSpecific = false; break; }
                for (int j = 0; j < a.length; j++) {
                    if (!b[j].isAssignableFrom(a[j])) { mostSpecific = false; break; }
                }
                if (!mostSpecific) break;
            }
            if (mostSpecific) return index;
        }
        List<String> choices = new ArrayList<>();
        for (int index : best) choices.add(Arrays.toString(signatures.get(index)));
        throw new IllegalArgumentException("Ambiguous Java overload for " + name + ": " + choices + "; use .overload(*types)");
    }

    // --- reflection helpers ----------------------------------------------------

    /**
     * Pick the best method for {@code (name, arity, args)}. Scores each
     * candidate by how well its formal parameter types match the runtime
     * argument types — higher is better.
     */
    private static Method findMethod(Class<?> klass, String name, int arity, Object[] args, boolean staticOnly) {
        // First pass: prefer non-bridge declared methods.
        Method best = pickByName(klass, name, arity, args, false, staticOnly);
        if (best != null) return best;
        // Fallback: include bridge methods (e.g. CharSequence.length() exposed
        // via bridges on StringBuilder).
        best = pickByName(klass, name, arity, args, true, staticOnly);
        if (best != null) return best;
        throw new NoSuchElementException("No method " + klass.getName() + "." + name
                + " with arity " + arity);
    }

    private static Method pickByName(Class<?> klass, String name, int arity,
                                     Object[] args, boolean allowBridge, boolean staticOnly) {
        Method best = null;
        int bestScore = -1;
        for (Method m : klass.getMethods()) {
            if (!m.getName().equals(name)) continue;
            if (Modifier.isStatic(m.getModifiers()) != staticOnly) continue;
            if (!m.isVarArgs() && m.getParameterCount() != arity) continue;
            if (m.isVarArgs() && arity < m.getParameterCount() - 1) continue;
            if (!allowBridge && (m.isBridge() || m.isSynthetic())) continue;
            int score = executableScore(m, args);
            if (score > bestScore) { bestScore = score; best = m; }
        }
        return best;
    }

    private static Constructor<?> findConstructor(Class<?> klass, int arity, Object[] args) {
        Constructor<?> best = null;
        int bestScore = -1;
        for (Constructor<?> c : klass.getConstructors()) {
            if (!c.isVarArgs() && c.getParameterCount() != arity) continue;
            if (c.isVarArgs() && arity < c.getParameterCount() - 1) continue;
            int score = executableScore(c, args);
            if (score > bestScore) { bestScore = score; best = c; }
        }
        if (best == null) {
            throw new NoSuchElementException("No constructor for " + klass.getName()
                    + " with arity " + arity);
        }
        return best;
    }

    /**
     * Match score for the whole arg list. Higher is better, -1 means at least
     * one arg is incompatible.
     */
    private static int score(Class<?>[] formals, Object[] args) {
        int total = 0;
        for (int i = 0; i < formals.length; i++) {
            int s = scoreOne(formals[i], args[i]);
            if (s < 0) return -1;
            total += s;
        }
        return total;
    }

    /**
     * Per-arg score:
     *   3 = natural fit (Double -> double/Double, Integer -> int/Integer, etc.)
     *   2 = same numeric family with widening (Integer -> long, Float -> double)
     *   1 = cross-family numeric coercion that loses information
     *       (Double -> int, Integer -> double when no better candidate exists)
     *   0 = JSON null in a non-primitive slot
     *  -1 = incompatible
     *
     * Without this fine-grained ranking we'd pick {@code Math.max(int,int)}
     * over {@code Math.max(double,double)} when given JSON 3.5.
     */
    private static int scoreOne(Class<?> formal, Object arg) {
        if (arg == null) return formal.isPrimitive() ? -1 : 1;
        Class<?> a = arg.getClass();

        if (formal.isAssignableFrom(a)) return formal == Object.class ? 1 : 3;
        if (formal.isArray() && arg instanceof List<?>) {
            for (Object item : (List<?>) arg) if (scoreOne(formal.getComponentType(), item) < 0) return -1;
            return 2;
        }
        if (formal.isEnum() && arg instanceof String) {
            try { enumValue(formal, (String) arg); return 2; } catch (IllegalArgumentException e) { return -1; }
        }
        if ((formal == char.class || formal == Character.class) && arg instanceof String) return ((String)arg).length() == 1 ? 3 : -1;
        if (formal == Set.class && arg instanceof List<?>) return 2;

        if (arg instanceof Number) {
            // Integer family — small whole numbers
            if (a == Integer.class || a == Short.class || a == Byte.class) {
                if (formal == int.class    || formal == Integer.class)  return 3;
                if (formal == long.class   || formal == Long.class)     return 2;
                if (formal == short.class  || formal == Short.class)    return 1;
                if (formal == byte.class   || formal == Byte.class)     return 1;
                if (formal == double.class || formal == Double.class)   return 2;
                if (formal == float.class  || formal == Float.class)    return 2;
            }
            // Long family
            if (a == Long.class) {
                if (formal == long.class   || formal == Long.class)     return 3;
                if (formal == double.class || formal == Double.class)   return 2;
                if (formal == float.class  || formal == Float.class)    return 1;
                if (formal == int.class    || formal == Integer.class)  return 1;
            }
            // Double family — fractional values
            if (a == Double.class || a == java.math.BigDecimal.class) {
                if (formal == double.class || formal == Double.class)   return 3;
                if (formal == float.class  || formal == Float.class)    return 2;
                if (formal == long.class   || formal == Long.class)     return 1;
                if (formal == int.class    || formal == Integer.class)  return 1;
            }
            // Float family
            if (a == Float.class) {
                if (formal == float.class  || formal == Float.class)    return 3;
                if (formal == double.class || formal == Double.class)   return 2;
            }
        }

        if (arg instanceof Boolean && (formal == boolean.class || formal == Boolean.class)) return 3;
        if (arg instanceof Character) {
            if (formal == char.class || formal == Character.class) return 3;
            if (formal == int.class || formal == long.class || formal == float.class || formal == double.class) return 2;
        }

        return -1;
    }

    // --- value encoding/decoding ----------------------------------------------

    private Object[] decodeArgs(JSONArray a) throws Exception {
        Object[] out = new Object[a.length()];
        for (int i = 0; i < a.length(); i++) out[i] = decode(a.get(i));
        return out;
    }

    Object decode(Object v) throws Exception {
        if (v == JSONObject.NULL) return null;
        if (v instanceof JSONObject) {
            JSONObject obj = (JSONObject) v;
            if (obj.has("__ref")) return registry.get(obj.getString("__ref"));
            if (obj.has("__callback")) {
                if (callbacks == null) throw new IllegalStateException("Callbacks unavailable");
                return callbacks.create(obj.getString("__callback"), obj.getString("interface"));
            }
            if (obj.has("__map")) {
                Map<Object, Object> out = new LinkedHashMap<>();
                JSONArray entries = obj.getJSONArray("__map");
                for (int i = 0; i < entries.length(); i++) {
                    JSONArray entry = entries.getJSONArray(i);
                    out.put(decode(entry.get(0)), decode(entry.get(1)));
                }
                return out;
            }
            Map<String, Object> out = new LinkedHashMap<>();
            for (String key : obj.keySet()) out.put(key, decode(obj.get(key)));
            return out;
        }
        if (v instanceof JSONArray) {
            List<Object> out = new ArrayList<>();
            JSONArray array = (JSONArray)v;
            for (int i = 0; i < array.length(); i++) out.add(decode(array.get(i)));
            return out;
        }
        return v; // primitives + Strings pass through
    }

    Object encode(Object v) { return encode(v, new IdentityHashMap<>()); }

    private Object encode(Object v, IdentityHashMap<Object, Boolean> seen) {
        if (v == null) return JSONObject.NULL;
        Class<?> c = v.getClass();
        if (v instanceof String || v instanceof Number || v instanceof Boolean) return v;
        if (v instanceof Character) return v.toString();
        if (c.isPrimitive()) return v;
        if ((c.isArray() || v instanceof Collection<?> || v instanceof Map<?, ?>) && !seen.containsKey(v)) {
            seen.put(v, Boolean.TRUE);
            try {
                if (c.isArray()) {
                    JSONArray out = new JSONArray();
                    for (int i = 0; i < Array.getLength(v); i++) out.put(encode(Array.get(v, i), seen));
                    return out;
                }
                if (v instanceof Collection<?>) {
                    JSONArray out = new JSONArray();
                    for (Object item : (Collection<?>) v) out.put(encode(item, seen));
                    return out;
                }
                Map<?, ?> map = (Map<?, ?>)v;
                JSONArray entries = new JSONArray();
                for (Map.Entry<?, ?> entry : map.entrySet()) entries.put(new JSONArray()
                    .put(encode(entry.getKey(), seen)).put(encode(entry.getValue(), seen)));
                return new JSONObject().put("__map", entries);
            } finally { seen.remove(v); }
        }
        // Anything else becomes an opaque ref
        String id = registry.register(v);
        return new JSONObject().put("__ref", id).put("__class", c.getName())
                .put("__kind", v instanceof Iterator<?> ? "iterator" : "object");
    }

    private static Object[] coerce(Class<?>[] types, Object[] args) {
        Object[] out = new Object[args.length];
        for (int i = 0; i < args.length; i++) out[i] = coerceOne(types[i], args[i]);
        return out;
    }

    static Object coerceOne(Class<?> target, Object v) {
        if (v == null) {
            if (target.isPrimitive()) throw new IllegalArgumentException("null cannot be assigned to " + target.getName());
            return null;
        }
        if (target.isInstance(v)) return v;
        if (target.isArray() && v instanceof List<?>) {
            List<?> list = (List<?>)v;
            Object array = Array.newInstance(target.getComponentType(), list.size());
            for (int i = 0; i < list.size(); i++) Array.set(array, i, coerceOne(target.getComponentType(), list.get(i)));
            return array;
        }
        if (target == Set.class && v instanceof List<?>) return new LinkedHashSet<>((List<?>)v);
        if (target.isEnum() && v instanceof String) return enumValue(target, (String)v);
        if ((target == char.class || target == Character.class) && v instanceof String && ((String)v).length() == 1) return ((String)v).charAt(0);
        if (v instanceof Character) {
            int code = (Character)v;
            if (target == int.class) return code;
            if (target == long.class) return (long)code;
            if (target == float.class) return (float)code;
            if (target == double.class) return (double)code;
        }
        if (v instanceof Number) {
            Number n = (Number) v;
            if (target == int.class    || target == Integer.class) return n.intValue();
            if (target == long.class   || target == Long.class)    return n.longValue();
            if (target == double.class || target == Double.class)  return n.doubleValue();
            if (target == float.class  || target == Float.class)   return n.floatValue();
            if (target == short.class  || target == Short.class)   return n.shortValue();
            if (target == byte.class   || target == Byte.class)    return n.byteValue();
        }
        if (target == boolean.class && v instanceof Boolean) return v;
        if (target == char.class && v instanceof Character) return v;
        throw new IllegalArgumentException("Cannot assign " + v.getClass().getName() + " to " + target.getName());
    }


    @SuppressWarnings({"unchecked", "rawtypes"})
    private static Object enumValue(Class<?> type, String value) { return Enum.valueOf((Class)type, value); }

    private static Class<?>[] parameterTypes(JSONArray names) throws ClassNotFoundException {
        Class<?>[] out = new Class<?>[names.length()];
        for (int i = 0; i < out.length; i++) out[i] = resolveType(names.getString(i));
        return out;
    }
    private static Class<?> resolveType(String name) throws ClassNotFoundException {
        if (name.endsWith("[]")) return Array.newInstance(resolveType(name.substring(0, name.length()-2)), 0).getClass();
        switch (name) {
            case "int": return int.class; case "long": return long.class;
            case "float": return float.class; case "double": return double.class;
            case "short": return short.class; case "byte": return byte.class;
            case "boolean": return boolean.class; case "char": return char.class;
            default: return Class.forName(name);
        }
    }
    private static int executableScore(Executable member, Object[] args) {
        try { return score(member.getParameterTypes(), pack(member, args)) - (member.isVarArgs() ? 1 : 0); }
        catch (IllegalArgumentException e) { return -1; }
    }
    private static Object[] pack(Executable member, Object[] args) {
        Class<?>[] types = member.getParameterTypes();
        if (!member.isVarArgs()) return args;
        int fixed = types.length - 1;
        if (args.length == types.length && (args[fixed] == null || types[fixed].isInstance(args[fixed]) || args[fixed] instanceof List<?>)) return args;
        if (args.length < fixed) throw new IllegalArgumentException("Missing varargs prefix");
        Object[] out = Arrays.copyOf(args, types.length);
        out[fixed] = Arrays.asList(Arrays.copyOfRange(args, fixed, args.length));
        return out;
    }
    private static Object[] adapt(Executable member, Object[] args) { return coerce(member.getParameterTypes(), pack(member, args)); }

    // Public methods implemented by non-public JDK collection/iterator classes
    // must be invoked through an accessible public interface, not setAccessible.
    private static Method accessibleMethod(Object target, Method method) {
        if (Modifier.isPublic(method.getDeclaringClass().getModifiers())) return method;
        Deque<Class<?>> queue = new ArrayDeque<>();
        queue.add(target.getClass());
        Set<Class<?>> seen = new HashSet<>();
        while (!queue.isEmpty()) {
            Class<?> type = queue.remove();
            if (!seen.add(type)) continue;
            if (Modifier.isPublic(type.getModifiers())) {
                try { return type.getMethod(method.getName(), method.getParameterTypes()); }
                catch (NoSuchMethodException ignored) { }
            }
            queue.addAll(Arrays.asList(type.getInterfaces()));
            if (type.getSuperclass() != null) queue.add(type.getSuperclass());
        }
        return method;
    }

    /** Mirrors java.util.NoSuchElementException without forcing a verbose import in callers. */
    static final class NoSuchElementException extends RuntimeException {
        NoSuchElementException(String msg) { super(msg); }
    }
}
