package org.operix.rpc;

import org.json.JSONObject;
import org.junit.jupiter.api.Test;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import static org.junit.jupiter.api.Assertions.*;

class ServerTest {
    @Test
    void exposesInvocationCauseAndPreservesRequestId() throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        String request = "{\"id\":42,\"class\":\"java.lang.Integer\",\"method\":\"parseInt\",\"static\":true,\"args\":[\"invalid\"]}\n";
        new Server(new PrintStream(output, true, "UTF-8")).run(
            new ByteArrayInputStream(request.getBytes(StandardCharsets.UTF_8)));
        JSONObject response = new JSONObject(output.toString("UTF-8"));
        assertEquals(42, response.getInt("id"));
        assertTrue(response.getString("error").contains("NumberFormatException"));
        assertFalse(response.getString("error").contains("InvocationTargetException"));
    }
}
