import com.sun.source.tree.*;
import com.sun.source.util.*;
import javax.tools.*;
import java.net.URI;
import java.util.*;
import java.util.jar.*;
import java.io.*;
import org.json.*;

/** Reads declaration names from the published sources, without resolving dependencies. */
public final class SourceParameters {
    public static void main(String[] args) throws Exception {
        List<JavaFileObject> files = new ArrayList<>();
        try (JarFile jar = new JarFile(args[0])) {
            for (JarEntry entry : Collections.list(jar.entries())) {
                if (!entry.getName().endsWith(".java")) continue;
                String source;
                try (InputStream in = jar.getInputStream(entry)) {
                    source = new String(in.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8);
                }
                final String contents = source;
                files.add(new SimpleJavaFileObject(URI.create("string:///" + entry.getName()), JavaFileObject.Kind.SOURCE) {
                    public CharSequence getCharContent(boolean ignore) { return contents; }
                });
            }
        }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("Java compiler module required");
        JavacTask task = (JavacTask) compiler.getTask(null, null, d -> {}, Arrays.asList("-proc:none"), null, files);
        JSONObject result = new JSONObject();
        for (CompilationUnitTree unit : task.parse()) {
            String pkg = unit.getPackageName() == null ? "" : unit.getPackageName().toString();
            new TreeScanner<Void, String>() {
                public Void visitClass(ClassTree cls, String enclosing) {
                    if (cls.getSimpleName().length() == 0) return null;
                    String name = enclosing == null ? pkg + "." + cls.getSimpleName() : enclosing + "$" + cls.getSimpleName();
                    return super.visitClass(cls, name);
                }
                public Void visitMethod(MethodTree method, String owner) {
                    if (owner == null) return null;
                    String name = method.getName().toString();
                    if (name.equals("<init>")) name = owner;
                    JSONArray parameters = new JSONArray();
                    for (VariableTree p : method.getParameters()) {
                        parameters.put(new JSONObject().put("name", p.getName().toString()).put("source_type", p.getType().toString()));
                    }
                    JSONArray members = result.optJSONArray(owner);
                    if (members == null) { members = new JSONArray(); result.put(owner, members); }
                    final boolean[] nullable = {false};
                    final JSONArray delegates = new JSONArray();
                    new TreeScanner<Void, Void>() {
                        public Void visitReturn(ReturnTree node, Void unused) {
                            ExpressionTree expression = node.getExpression();
                            if (expression != null && expression.getKind() == Tree.Kind.NULL_LITERAL) nullable[0] = true;
                            if (expression instanceof MethodInvocationTree) {
                                MethodInvocationTree call = (MethodInvocationTree)expression;
                                ExpressionTree select = call.getMethodSelect();
                                if (select instanceof IdentifierTree) delegates.put(new JSONObject()
                                    .put("name", select.toString()).put("arity", call.getArguments().size()));
                            }
                            return null;
                        }
                        public Void visitLambdaExpression(LambdaExpressionTree node, Void unused) { return null; }
                        public Void visitClass(ClassTree node, Void unused) { return null; }
                    }.scan(method.getBody(), null);
                    members.put(new JSONObject().put("name", name).put("parameters", parameters)
                        .put("nullable_return", nullable[0]).put("return_calls", delegates));
                    // Local/anonymous classes aren't part of the public API inventory.
                    return null;
                }
            }.scan(unit, null);
        }
        System.out.println(result);
    }
}
