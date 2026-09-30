import java.lang.reflect.*;
import java.util.*;
import java.util.jar.JarFile;
import org.json.JSONArray;
import org.json.JSONObject;

/** Public API inventory from the exact artifact, without class initialization. */
public final class ApiInventory {
    private static JSONArray types(Class<?>[] types) {
        JSONArray out = new JSONArray();
        for (Class<?> type : types) out.put(type.getTypeName());
        return out;
    }

    private static JSONArray parameters(Executable member) {
        JSONArray out = new JSONArray();
        for (Parameter p : member.getParameters()) {
            out.put(new JSONObject().put("name", p.getName())
                .put("name_present", p.isNamePresent()).put("type", p.getType().getTypeName())
                .put("generic_type", p.getParameterizedType().getTypeName()));
        }
        return out;
    }

    private static JSONObject executable(Executable member) {
        return new JSONObject().put("name", member.getName())
            .put("declaring_class", member.getDeclaringClass().getName())
            .put("parameters", parameters(member)).put("varargs", member.isVarArgs())
            .put("exceptions", types(member.getExceptionTypes()))
            .put("static", Modifier.isStatic(member.getModifiers()));
    }

    public static void main(String[] args) throws Exception {
        PrintStreamGuard guard = new PrintStreamGuard();
        List<String> names = new ArrayList<>();
        try (JarFile jar = new JarFile(args[0])) {
            jar.stream().map(entry -> entry.getName())
                .filter(name -> name.endsWith(".class"))
                .filter(name -> name.startsWith("org/sikuli/") || name.startsWith("com/sikulix/"))
                .map(name -> name.substring(0, name.length() - 6).replace('/', '.'))
                .forEach(names::add);
        }
        Collections.sort(names);
        JSONArray classes = new JSONArray();
        JSONArray errors = new JSONArray();
        for (String name : names) {
            try {
                Class<?> cls = Class.forName(name, false, ApiInventory.class.getClassLoader());
                if (!Modifier.isPublic(cls.getModifiers()) || cls.isSynthetic()) continue;
                Class<?> enclosing = cls.getEnclosingClass();
                if (enclosing != null && !Modifier.isPublic(enclosing.getModifiers())) continue;
                JSONObject row = new JSONObject().put("class", name)
                    .put("interface", cls.isInterface()).put("enum", cls.isEnum())
                    .put("superclass", cls.getSuperclass() == null ? JSONObject.NULL : cls.getSuperclass().getName())
                    .put("interfaces", types(cls.getInterfaces()));
                List<Method> methods = new ArrayList<>(Arrays.asList(cls.getMethods()));
                methods.sort(Comparator.comparing(Method::toGenericString));
                JSONArray methodRows = new JSONArray();
                for (Method m : methods) {
                    if (m.isSynthetic() || m.isBridge()) continue;
                    methodRows.put(executable(m).put("return_type", m.getReturnType().getTypeName())
                        .put("generic_return_type", m.getGenericReturnType().getTypeName())
                        .put("inherited", m.getDeclaringClass() != cls));
                }
                List<Constructor<?>> constructors = new ArrayList<>(Arrays.asList(cls.getConstructors()));
                constructors.sort(Comparator.comparing(Constructor::toGenericString));
                JSONArray constructorRows = new JSONArray();
                for (Constructor<?> c : constructors) {
                    if (!c.isSynthetic()) constructorRows.put(executable(c));
                }
                List<Field> fields = new ArrayList<>(Arrays.asList(cls.getFields()));
                fields.sort(Comparator.comparing(Field::toGenericString));
                JSONArray fieldRows = new JSONArray();
                for (Field f : fields) {
                    if (f.isSynthetic()) continue;
                    fieldRows.put(new JSONObject().put("name", f.getName())
                        .put("declaring_class", f.getDeclaringClass().getName())
                        .put("type", f.getType().getTypeName())
                        .put("static", Modifier.isStatic(f.getModifiers()))
                        .put("final", Modifier.isFinal(f.getModifiers())));
                }
                classes.put(row.put("methods", methodRows).put("constructors", constructorRows).put("fields", fieldRows));
            } catch (LinkageError | ReflectiveOperationException | RuntimeException e) {
                errors.put(new JSONObject().put("class", name).put("error", e.toString()));
            }
        }
        guard.out.println(new JSONObject().put("classes", classes).put("unavailable_classes", errors));
    }

    private static final class PrintStreamGuard {
        final java.io.PrintStream out = System.out;
        PrintStreamGuard() { System.setOut(System.err); }
    }
}
