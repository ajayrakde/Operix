package org.operix.rpc;

import javax.swing.*;
import java.awt.*;
import java.io.*;
import org.json.*;

/** Deterministic real desktop app used by the bridge's capture/OCR/input tests. */
public final class DesktopFixture {
    private static JFrame frame;
    private static JTextField field;
    private static JLabel label;
    private static JButton button;
    private static boolean clicked;
    private static JSONObject rectangle(Component component) {
        Point p = component.getLocationOnScreen();
        return new JSONObject().put("x", p.x).put("y", p.y).put("w", component.getWidth()).put("h", component.getHeight());
    }
    public static void main(String[] args) throws Exception {
        SwingUtilities.invokeAndWait(() -> {
            frame = new JFrame("Operix desktop validation");
            frame.setDefaultCloseOperation(WindowConstants.DISPOSE_ON_CLOSE);
            frame.setUndecorated(true);
            JPanel content = new JPanel(null);
            content.setBackground(Color.WHITE);
            content.setPreferredSize(new Dimension(850, 320));
            label = new JLabel("Submit 12345", SwingConstants.CENTER);
            label.setFont(new Font("SansSerif", Font.PLAIN, 44));
            label.setBounds(30, 20, 780, 90);
            content.add(label);
            field = new JTextField();
            field.setFont(new Font("SansSerif", Font.PLAIN, 24));
            field.setBounds(50, 140, 520, 60);
            content.add(field);
            button = new JButton("Click me");
            button.setFont(new Font("SansSerif", Font.PLAIN, 24));
            button.setBounds(590, 140, 200, 60);
            button.addActionListener(e -> clicked = true);
            content.add(button);
            frame.setContentPane(content);
            frame.pack(); frame.setLocation(80, 80); frame.setAlwaysOnTop(true); frame.setVisible(true);
        });
        Thread.sleep(700); // Wait for native map/configure events before reading screen coordinates.
        new Robot().waitForIdle();
        SwingUtilities.invokeAndWait(() -> System.out.println(new JSONObject()
            .put("region", rectangle(frame.getContentPane())).put("label", rectangle(label))
            .put("field", rectangle(field)).put("button", rectangle(button))));
        if (args.length > 0) {
            File folder = new File(args[0]); folder.mkdirs();
            javax.imageio.ImageIO.write(new Robot().createScreenCapture(new Rectangle(Toolkit.getDefaultToolkit().getScreenSize())),
                "png", new File(folder, "fixture-desktop.png"));
        }
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        String command;
        while ((command = reader.readLine()) != null) {
            if (command.equals("quit")) break;
            if (command.equals("state")) SwingUtilities.invokeAndWait(() -> System.out.println(
                new JSONObject().put("clicked", clicked).put("text", field.getText())));
        }
        SwingUtilities.invokeAndWait(() -> frame.dispose());
    }
}
