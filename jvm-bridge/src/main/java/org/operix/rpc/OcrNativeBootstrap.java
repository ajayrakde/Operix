package org.operix.rpc;

import com.sun.jna.Library;
import com.sun.jna.NativeLibrary;
import com.sun.jna.Platform;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.HashMap;
import java.util.Map;

/** Keeps Oculix 4.0.0's Tess4J binding on the bundled Linux native pair. */
final class OcrNativeBootstrap {
    // Retain JNA handles for the lifetime of the process.
    private static NativeLibrary leptonica;
    private static NativeLibrary tesseract;

    private OcrNativeBootstrap() { }

    static synchronized void initialize() throws IOException {
        if (!Platform.isLinux() || tesseract != null) return;
        String tier = resourceTier();
        Path dir = Paths.get(System.getProperty("user.home"), ".cache", "operix",
                "ocr-oculix-4.0.0", tier).toAbsolutePath();
        Files.createDirectories(dir);
        // Exact unversioned names win JNA's initial lookup. Without these,
        // JNA ranks *all* versioned candidates and picks system 5.0.3 over 5.
        extract(tier + "/libleptonica.so.6", dir.resolve("libleptonica.so"));
        extract(tier + "/libtesseract.so.5", dir.resolve("libtesseract.so"));
        Map<String, Object> options = new HashMap<>();
        // RTLD_LAZY | RTLD_GLOBAL: bundled Leptonica must satisfy Tesseract's
        // DT_NEEDED even when the old payload has a broken $ORIGIN RUNPATH.
        options.put(Library.OPTION_OPEN_FLAGS, 0x101);
        leptonica = NativeLibrary.getInstance(dir.resolve("libleptonica.so").toString(), options);
        NativeLibrary.addSearchPath("leptonica", dir.toString());
        NativeLibrary.addSearchPath("tesseract", dir.toString());
        tesseract = NativeLibrary.getInstance("tesseract", options);
        if (!Files.isSameFile(tesseract.getFile().toPath(), dir.resolve("libtesseract.so"))) {
            throw new IOException("OCR bound a system Tesseract instead of the bundled library");
        }
        String version = tesseract.getFunction("TessVersion").invokeString(new Object[0], false);
        if (!version.startsWith("5.5.")) {
            throw new IOException("Bundled OCR library reports unexpected Tesseract version: " + version);
        }
    }

    static String resourceTier() {
        String prefix = Platform.RESOURCE_PREFIX;
        String glibc = NativeLibrary.getInstance("c").getFunction("gnu_get_libc_version")
                .invokeString(new Object[0], false);
        String[] parts = glibc.split("\\.");
        int major = Integer.parseInt(parts[0]);
        int minor = Integer.parseInt(parts[1]);
        return prefix + (major > 2 || major == 2 && minor >= 38 ? "" : "-legacy");
    }

    private static void extract(String resource, Path target) throws IOException {
        if (Files.isRegularFile(target)) return;
        Path temp = Files.createTempFile(target.getParent(), "native-", ".tmp");
        try (InputStream in = OcrNativeBootstrap.class.getResourceAsStream("/" + resource)) {
            if (in == null) throw new IOException("Bundled OCR native resource missing: " + resource);
            Files.copy(in, temp, StandardCopyOption.REPLACE_EXISTING);
            // Same-directory move ensures another bridge never sees a partial file.
            Files.move(temp, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } finally {
            Files.deleteIfExists(temp);
        }
    }
}
