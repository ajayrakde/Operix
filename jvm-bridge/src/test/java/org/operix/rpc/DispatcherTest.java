package org.operix.rpc;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/** Validates the JSON-RPC dispatch logic against a stub class that has nothing to do with OculiX. */
class DispatcherTest {

    private ObjectRegistry registry;
    private Dispatcher dispatcher;

    @BeforeEach
    void setup() {
        registry = new ObjectRegistry();
        dispatcher = new Dispatcher(registry);
    }

    // --- stub class used by the tests -----------------------------------------
    public static class Calculator {
        private int total;
        public Calculator() {}
        public Calculator(int initial) { this.total = initial; }
        public int add(int x) { total += x; return total; }
        public int multiply(int x, int y) { return x * y; }
        public static String greet(String name) { return "hello " + name; }
        public Calculator chain() { return this; }
        public Object nullable() { return null; }

        // Overloaded — same name, same arity, different param types
        public String describe(String s)  { return "string:" + s; }
        public String describe(int i)     { return "int:" + i; }
        public String describe(boolean b) { return "bool:" + b; }
    }

    @Test
    void constructor_no_args_returns_ref() throws Exception {
        JSONObject req = new JSONObject()
                .put("class", Calculator.class.getName())
                .put("args", new JSONArray());
        JSONObject res = dispatcher.dispatch(req);
        JSONObject result = res.getJSONObject("result");
        assertTrue(result.has("__ref"));
        assertEquals(Calculator.class.getName(), result.getString("__class"));
    }

    @Test
    void constructor_with_int_arg_then_instance_call() throws Exception {
        JSONObject ctor = new JSONObject()
                .put("class", Calculator.class.getName())
                .put("args", new JSONArray().put(10));
        String ref = dispatcher.dispatch(ctor).getJSONObject("result").getString("__ref");

        JSONObject add = new JSONObject()
                .put("ref", ref)
                .put("method", "add")
                .put("args", new JSONArray().put(5));
        assertEquals(15, dispatcher.dispatch(add).getInt("result"));

        JSONObject add2 = new JSONObject()
                .put("ref", ref)
                .put("method", "add")
                .put("args", new JSONArray().put(7));
        assertEquals(22, dispatcher.dispatch(add2).getInt("result"));
    }

    @Test
    void static_method_call_returns_string() throws Exception {
        JSONObject req = new JSONObject()
                .put("class", Calculator.class.getName())
                .put("method", "greet")
                .put("static", true)
                .put("args", new JSONArray().put("world"));
        assertEquals("hello world", dispatcher.dispatch(req).getString("result"));
    }

    @Test
    void multi_arg_method_with_numeric_coercion() throws Exception {
        JSONObject ctor = new JSONObject()
                .put("class", Calculator.class.getName())
                .put("args", new JSONArray());
        String ref = dispatcher.dispatch(ctor).getJSONObject("result").getString("__ref");

        // JSON only knows "Number" — ensure we coerce double -> int when the method needs ints
        JSONObject mul = new JSONObject()
                .put("ref", ref)
                .put("method", "multiply")
                .put("args", new JSONArray().put(6).put(7));
        assertEquals(42, dispatcher.dispatch(mul).getInt("result"));
    }

    @Test
    void object_returning_method_yields_ref_and_round_trip_works() throws Exception {
        JSONObject ctor = new JSONObject()
                .put("class", Calculator.class.getName())
                .put("args", new JSONArray());
        String refA = dispatcher.dispatch(ctor).getJSONObject("result").getString("__ref");

        JSONObject chain = new JSONObject()
                .put("ref", refA)
                .put("method", "chain")
                .put("args", new JSONArray());
        JSONObject chainResult = dispatcher.dispatch(chain).getJSONObject("result");
        assertTrue(chainResult.has("__ref"));
        // Identity interning: same Java instance -> same ref id
        assertEquals(refA, chainResult.getString("__ref"));
    }

    @Test
    void null_return_is_encoded_as_json_null() throws Exception {
        JSONObject ctor = new JSONObject()
                .put("class", Calculator.class.getName())
                .put("args", new JSONArray());
        String ref = dispatcher.dispatch(ctor).getJSONObject("result").getString("__ref");

        JSONObject req = new JSONObject()
                .put("ref", ref)
                .put("method", "nullable")
                .put("args", new JSONArray());
        assertEquals(JSONObject.NULL, dispatcher.dispatch(req).get("result"));
    }

    @Test
    void release_drops_the_reference() throws Exception {
        JSONObject ctor = new JSONObject()
                .put("class", Calculator.class.getName())
                .put("args", new JSONArray());
        String ref = dispatcher.dispatch(ctor).getJSONObject("result").getString("__ref");

        dispatcher.dispatch(new JSONObject().put("ref", ref).put("release", true));

        assertThrows(IllegalArgumentException.class,
                () -> dispatcher.dispatch(new JSONObject().put("ref", ref).put("method", "add")
                        .put("args", new JSONArray().put(1))));
    }

    @Test
    void overload_resolution_picks_double_when_arg_is_fractional() throws Exception {
        // Regression: Math.max has int/long/float/double overloads. A JSON
        // 3.5 (parsed as Double) must hit Math.max(double,double), not the
        // int overload that would silently truncate to 3.
        JSONObject req = new JSONObject()
                .put("class", "java.lang.Math")
                .put("method", "max")
                .put("static", true)
                .put("args", new JSONArray().put(3.5).put(2.5));
        assertEquals(3.5, dispatcher.dispatch(req).getDouble("result"), 0.0001);
    }

    @Test
    void overload_resolution_by_arg_type() throws Exception {
        JSONObject ctor = new JSONObject()
                .put("class", Calculator.class.getName())
                .put("args", new JSONArray());
        String ref = dispatcher.dispatch(ctor).getJSONObject("result").getString("__ref");

        // String -> describe(String)
        assertEquals("string:hi", dispatcher.dispatch(new JSONObject()
                .put("ref", ref).put("method", "describe")
                .put("args", new JSONArray().put("hi"))).getString("result"));

        // Int -> describe(int)
        assertEquals("int:42", dispatcher.dispatch(new JSONObject()
                .put("ref", ref).put("method", "describe")
                .put("args", new JSONArray().put(42))).getString("result"));

        // Bool -> describe(boolean)
        assertEquals("bool:true", dispatcher.dispatch(new JSONObject()
                .put("ref", ref).put("method", "describe")
                .put("args", new JSONArray().put(true))).getString("result"));
    }

    @Test
    void unknown_class_raises() {
        JSONObject req = new JSONObject()
                .put("class", "no.such.Class")
                .put("args", new JSONArray());
        assertThrows(ClassNotFoundException.class, () -> dispatcher.dispatch(req));
    }
    public static class Compatibility {
        public static String number(Number value) { return value.getClass().getSimpleName(); }
        public static String choose(Number value) { return "number"; }
        public static String choose(java.io.Serializable value) { return "serializable"; }
        public static String serializable(java.io.Serializable value) { return value.toString(); }
        public static String text(Comparable<?> value) { return value.toString(); }
        public static int list(java.util.AbstractList<?> value) { return value.size(); }
        public static boolean callback(boolean value) { return value; }
        public static int character(int value) { return value; }
    }

    private JSONObject exact(String method, String type, Object value) throws Exception {
        return dispatcher.dispatch(new JSONObject().put("class", Compatibility.class.getName())
            .put("method", method).put("static", true).put("parameter_types", new JSONArray().put(type))
            .put("args", new JSONArray().put(value)));
    }

    @Test
    void validJavaInterfacesAndNumericSupertypesRemainAccepted() throws Exception {
        assertEquals(Compatibility.number(3), exact("number", "java.lang.Number", 3).getString("result"));
        assertEquals(Compatibility.text("hello"), exact("text", "java.lang.Comparable", "hello").getString("result"));
        assertEquals(Compatibility.list(new java.util.ArrayList<>(java.util.Arrays.asList(1, 2))),
            exact("list", "java.util.AbstractList", new JSONArray().put(1).put(2)).getInt("result"));
        org.sikuli.script.FindFailed failure = new org.sikuli.script.FindFailed("missing");
        String locationRef = registry.register(failure);
        assertTrue(dispatcher.decode(new JSONObject().put("__ref", locationRef)) instanceof java.io.Serializable);
        assertEquals(Compatibility.serializable(failure), exact("serializable", "java.io.Serializable",
            new JSONObject().put("__ref", locationRef)).getString("result"));
    }

    @Test
    void overloadUsesJvmSpecificityBeyondTheInventory() throws Exception {
        JSONArray candidates = new JSONArray();
        for (String type : new String[]{"java.io.Serializable", "java.lang.Number"}) candidates.put(new JSONObject()
            .put("parameter_types", new JSONArray().put(type)).put("args", new JSONArray().put(3)));
        int index = dispatcher.dispatch(new JSONObject().put("class", Compatibility.class.getName())
            .put("resolve", "choose").put("candidates", candidates)).getInt("result");
        assertEquals(1, index);
        assertEquals("number", Compatibility.choose(3));
    }

    @Test
    void callbackValidationAcceptsJavaUnboxingAndRejectsIncompatibleValues() throws Exception {
        assertEquals(Compatibility.callback(Boolean.TRUE), Dispatcher.coerceOne(boolean.class, Boolean.TRUE));
        assertEquals(Compatibility.character(Character.valueOf('A')), Dispatcher.coerceOne(int.class, Character.valueOf('A')));
        assertThrows(IllegalArgumentException.class, () -> Dispatcher.coerceOne(boolean.class, "true"));
        assertThrows(IllegalArgumentException.class, () -> Compatibility.class.getMethod("callback", boolean.class).invoke(null, "true"));
        assertThrows(IllegalArgumentException.class, () -> Dispatcher.coerceOne(int.class, null));
    }

}
