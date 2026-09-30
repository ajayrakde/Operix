# Python wrapper coverage against Oculix 4.0.0

Generated from the pinned bridge JAR by `tools/inventory_java_api.py`.

**Name and arity coverage is not verified semantic parity.** It only means an
explicit Python method accepts the Java argument count and has matching
static/instance placement. It does not verify parameter types, overload
selection, return annotations, defaults, callbacks or runtime behavior.

The complete machine inventory includes inherited methods, constructors,
public fields, exception types and generic types. `java.lang.Object` methods
are retained in that inventory but excluded from coverage counts below.

- Public Java classes/interfaces/enums inventoried: **211**.
- Java types with a Python class facade: **211** (including the static OCR facade).
- Public method overloads across classes, including inheritance: **13574**.
- Overloads with an explicit Python name and matching arity/staticness: **13574**.
- Remaining method overloads: **0**.
- Constructors and fields are inventoried but not included in method-coverage totals.
- Dynamic forwarding is not counted as explicit coverage.
- The broad inventory includes Oculix support, remote and guide packages, not only desktop automation.

## Existing wrapper classes

| Java class | Overloads | Explicit name + arity | Missing or incompatible |
|---|---:|---:|---:|
| `com.sikulix.ocr.AmountVariantGenerator` | 2 | 2 | 0 |
| `com.sikulix.ocr.OCREngine` | 7 | 7 | 0 |
| `com.sikulix.ocr.PaddleOCRClient` | 11 | 11 | 0 |
| `com.sikulix.ocr.PaddleOCREngine` | 8 | 8 | 0 |
| `com.sikulix.ocr.TesseractEngine` | 9 | 9 | 0 |
| `com.sikulix.opencv.Sikulix` | 1 | 1 | 0 |
| `com.sikulix.tigervnc.Sikulix` | 1 | 1 | 0 |
| `com.sikulix.util.SSHTunnel` | 7 | 7 | 0 |
| `com.sikulix.util.SikuliLogger` | 4 | 4 | 0 |
| `com.sikulix.util.TextNormalizer` | 4 | 4 | 0 |
| `com.sikulix.vnc.VNCClient` | 53 | 53 | 0 |
| `com.sikulix.vnc.VNCClipboard` | 1 | 1 | 0 |
| `com.sikulix.vnc.VNCClipboard$Charset` | 1 | 1 | 0 |
| `com.sikulix.vnc.VNCClipboard$TextType` | 1 | 1 | 0 |
| `com.sikulix.vnc.VNCClipboard$TransferType` | 2 | 2 | 0 |
| `org.sikuli.android.ADBClient` | 7 | 7 | 0 |
| `org.sikuli.android.ADBDevice` | 30 | 30 | 0 |
| `org.sikuli.android.ADBRobot` | 28 | 28 | 0 |
| `org.sikuli.android.ADBScreen` | 310 | 310 | 0 |
| `org.sikuli.android.ADBTest` | 2 | 2 | 0 |
| `org.sikuli.basics.Debug` | 54 | 54 | 0 |
| `org.sikuli.basics.GenericHotkeyManager` | 13 | 13 | 0 |
| `org.sikuli.basics.HotkeyEvent` | 0 | 0 | 0 |
| `org.sikuli.basics.HotkeyListener` | 2 | 2 | 0 |
| `org.sikuli.basics.HotkeyManager` | 13 | 13 | 0 |
| `org.sikuli.basics.LinuxHotkeyManager` | 13 | 13 | 0 |
| `org.sikuli.basics.OS` | 11 | 11 | 0 |
| `org.sikuli.basics.PreferencesUser` | 81 | 81 | 0 |
| `org.sikuli.basics.Settings` | 15 | 15 | 0 |
| `org.sikuli.basics.SplashFrame` | 329 | 329 | 0 |
| `org.sikuli.guide.AnimationFactory` | 2 | 2 | 0 |
| `org.sikuli.guide.Animator` | 5 | 5 | 0 |
| `org.sikuli.guide.ClickableWindow` | 341 | 341 | 0 |
| `org.sikuli.guide.ComponentMover` | 16 | 16 | 0 |
| `org.sikuli.guide.GlobalMouseMotionListener` | 2 | 2 | 0 |
| `org.sikuli.guide.GlobalMouseMotionTracker` | 5 | 5 | 0 |
| `org.sikuli.guide.Guide` | 364 | 364 | 0 |
| `org.sikuli.guide.IAnimator` | 2 | 2 | 0 |
| `org.sikuli.guide.Run` | 2 | 2 | 0 |
| `org.sikuli.guide.ShadowRenderer` | 2 | 2 | 0 |
| `org.sikuli.guide.SxAnchor` | 418 | 418 | 0 |
| `org.sikuli.guide.SxAnchor$AnchorListener` | 2 | 2 | 0 |
| `org.sikuli.guide.SxArea` | 417 | 417 | 0 |
| `org.sikuli.guide.SxArrow` | 418 | 418 | 0 |
| `org.sikuli.guide.SxBeam` | 334 | 334 | 0 |
| `org.sikuli.guide.SxBracket` | 410 | 410 | 0 |
| `org.sikuli.guide.SxButton` | 417 | 417 | 0 |
| `org.sikuli.guide.SxCallout` | 409 | 409 | 0 |
| `org.sikuli.guide.SxCircle` | 409 | 409 | 0 |
| `org.sikuli.guide.SxClickable` | 417 | 417 | 0 |
| `org.sikuli.guide.SxFlag` | 410 | 410 | 0 |
| `org.sikuli.guide.SxHotspot` | 417 | 417 | 0 |
| `org.sikuli.guide.SxImage` | 411 | 411 | 0 |
| `org.sikuli.guide.SxMagnet` | 5 | 5 | 0 |
| `org.sikuli.guide.SxRectangle` | 409 | 409 | 0 |
| `org.sikuli.guide.SxSpotlight` | 410 | 410 | 0 |
| `org.sikuli.guide.SxText` | 409 | 409 | 0 |
| `org.sikuli.guide.TimeoutTransition` | 2 | 2 | 0 |
| `org.sikuli.guide.Tracker` | 44 | 44 | 0 |
| `org.sikuli.guide.Transition` | 1 | 1 | 0 |
| `org.sikuli.guide.Transition$TransitionListener` | 1 | 1 | 0 |
| `org.sikuli.guide.TransitionDialog` | 334 | 334 | 0 |
| `org.sikuli.guide.Visual` | 408 | 408 | 0 |
| `org.sikuli.guide.Visual$Layout` | 11 | 11 | 0 |
| `org.sikuli.hotkey.HotkeyCallback` | 2 | 2 | 0 |
| `org.sikuli.hotkey.HotkeyController` | 7 | 7 | 0 |
| `org.sikuli.hotkey.HotkeyEvent` | 2 | 2 | 0 |
| `org.sikuli.hotkey.Keys` | 13 | 13 | 0 |
| `org.sikuli.hotkey.Keys$Modifier` | 0 | 0 | 0 |
| `org.sikuli.natives.CommandExecutorException` | 14 | 14 | 0 |
| `org.sikuli.natives.CommandExecutorHelper` | 1 | 1 | 0 |
| `org.sikuli.natives.CommandExecutorResult` | 3 | 3 | 0 |
| `org.sikuli.natives.GenericOsUtil` | 10 | 10 | 0 |
| `org.sikuli.natives.LinuxUtil` | 10 | 10 | 0 |
| `org.sikuli.natives.MacUtil` | 10 | 10 | 0 |
| `org.sikuli.natives.OSUtil` | 10 | 10 | 0 |
| `org.sikuli.natives.OSUtil$OsProcess` | 4 | 4 | 0 |
| `org.sikuli.natives.OSUtil$OsWindow` | 7 | 7 | 0 |
| `org.sikuli.natives.SXUser32` | 117 | 117 | 0 |
| `org.sikuli.natives.SysUtil` | 1 | 1 | 0 |
| `org.sikuli.natives.WinUtil` | 15 | 15 | 0 |
| `org.sikuli.natives.mac.jna.CoreGraphics` | 2 | 2 | 0 |
| `org.sikuli.natives.mac.jna.CoreGraphics$CGPoint` | 31 | 31 | 0 |
| `org.sikuli.natives.mac.jna.CoreGraphics$CGRect` | 31 | 31 | 0 |
| `org.sikuli.natives.mac.jna.CoreGraphics$CGRect$CGRectByValue` | 31 | 31 | 0 |
| `org.sikuli.natives.mac.jna.CoreGraphics$CGRectRef` | 31 | 31 | 0 |
| `org.sikuli.natives.mac.jna.CoreGraphics$CGRectRef$CGRectByReference` | 31 | 31 | 0 |
| `org.sikuli.natives.mac.jna.CoreGraphics$CGSize` | 31 | 31 | 0 |
| `org.sikuli.natives.mac.jna.ObjC` | 4 | 4 | 0 |
| `org.sikuli.script.App` | 57 | 57 | 0 |
| `org.sikuli.script.Button` | 0 | 0 | 0 |
| `org.sikuli.script.Constants` | 0 | 0 | 0 |
| `org.sikuli.script.Element` | 37 | 37 | 0 |
| `org.sikuli.script.Env` | 18 | 18 | 0 |
| `org.sikuli.script.FindFailed` | 26 | 26 | 0 |
| `org.sikuli.script.FindFailedResponse` | 11 | 11 | 0 |
| `org.sikuli.script.Finder` | 26 | 26 | 0 |
| `org.sikuli.script.Image` | 119 | 119 | 0 |
| `org.sikuli.script.ImageCallback` | 1 | 1 | 0 |
| `org.sikuli.script.ImagePath` | 43 | 43 | 0 |
| `org.sikuli.script.ImagePath$PathEntry` | 11 | 11 | 0 |
| `org.sikuli.script.Key` | 17 | 17 | 0 |
| `org.sikuli.script.KeyModifier` | 1 | 1 | 0 |
| `org.sikuli.script.Location` | 44 | 44 | 0 |
| `org.sikuli.script.Match` | 295 | 295 | 0 |
| `org.sikuli.script.MatchUtils` | 2 | 2 | 0 |
| `org.sikuli.script.Matches` | 6 | 6 | 0 |
| `org.sikuli.script.Mouse` | 24 | 24 | 0 |
| `org.sikuli.script.OCR` | 16 | 16 | 0 |
| `org.sikuli.script.OCR$OEM` | 11 | 11 | 0 |
| `org.sikuli.script.OCR$Options` | 33 | 33 | 0 |
| `org.sikuli.script.OCR$PSM` | 11 | 11 | 0 |
| `org.sikuli.script.ObserveEvent` | 31 | 31 | 0 |
| `org.sikuli.script.ObserveEvent$Type` | 11 | 11 | 0 |
| `org.sikuli.script.ObserverCallBack` | 8 | 8 | 0 |
| `org.sikuli.script.OculixKeywords` | 43 | 43 | 0 |
| `org.sikuli.script.OculixTimeoutException` | 13 | 13 | 0 |
| `org.sikuli.script.Offset` | 11 | 11 | 0 |
| `org.sikuli.script.Pattern` | 35 | 35 | 0 |
| `org.sikuli.script.Region` | 279 | 279 | 0 |
| `org.sikuli.script.SX` | 15 | 15 | 0 |
| `org.sikuli.script.SX$Log` | 1 | 1 | 0 |
| `org.sikuli.script.Screen` | 322 | 322 | 0 |
| `org.sikuli.script.ScreenImage` | 19 | 19 | 0 |
| `org.sikuli.script.ScreenOperationException` | 13 | 13 | 0 |
| `org.sikuli.script.SikuliEvent` | 31 | 31 | 0 |
| `org.sikuli.script.SikuliException` | 14 | 14 | 0 |
| `org.sikuli.script.SikuliXception` | 13 | 13 | 0 |
| `org.sikuli.script.TextRecognizer` | 19 | 19 | 0 |
| `org.sikuli.script.compare.DistanceComparator` | 8 | 8 | 0 |
| `org.sikuli.script.compare.HorizontalComparator` | 8 | 8 | 0 |
| `org.sikuli.script.compare.VerticalComparator` | 8 | 8 | 0 |
| `org.sikuli.support.ActionLogRenderer` | 1 | 1 | 0 |
| `org.sikuli.support.ActionLogRenderer$Mode` | 11 | 11 | 0 |
| `org.sikuli.support.AppLauncher` | 3 | 3 | 0 |
| `org.sikuli.support.AppLauncher$VncCommandBuilder` | 6 | 6 | 0 |
| `org.sikuli.support.CommandExecutor` | 11 | 11 | 0 |
| `org.sikuli.support.Commons` | 145 | 145 | 0 |
| `org.sikuli.support.Commons$Interpolation` | 11 | 11 | 0 |
| `org.sikuli.support.FileManager` | 44 | 44 | 0 |
| `org.sikuli.support.FileManager$FileFilter` | 1 | 1 | 0 |
| `org.sikuli.support.FindFailedDialog` | 317 | 317 | 0 |
| `org.sikuli.support.ImageGroup` | 7 | 7 | 0 |
| `org.sikuli.support.Observer` | 10 | 10 | 0 |
| `org.sikuli.support.Observer$State` | 11 | 11 | 0 |
| `org.sikuli.support.Observing` | 19 | 19 | 0 |
| `org.sikuli.support.PngChunk` | 2 | 2 | 0 |
| `org.sikuli.support.RemoteMode` | 14 | 14 | 0 |
| `org.sikuli.support.RemotePreflightCheck` | 6 | 6 | 0 |
| `org.sikuli.support.RemotePreflightCheck$CheckResult` | 0 | 0 | 0 |
| `org.sikuli.support.TesseractLastSeen` | 4 | 4 | 0 |
| `org.sikuli.support.animators.Animator` | 2 | 2 | 0 |
| `org.sikuli.support.animators.AnimatorLinear` | 2 | 2 | 0 |
| `org.sikuli.support.animators.AnimatorLinearInterpolation` | 2 | 2 | 0 |
| `org.sikuli.support.animators.AnimatorOutQuarticEase` | 2 | 2 | 0 |
| `org.sikuli.support.animators.AnimatorPulse` | 2 | 2 | 0 |
| `org.sikuli.support.animators.AnimatorQuarticEase` | 2 | 2 | 0 |
| `org.sikuli.support.animators.AnimatorStopExtention` | 2 | 2 | 0 |
| `org.sikuli.support.animators.AnimatorTimeBased` | 2 | 2 | 0 |
| `org.sikuli.support.animators.AnimatorTimeValueFunction` | 2 | 2 | 0 |
| `org.sikuli.support.devices.Device` | 19 | 19 | 0 |
| `org.sikuli.support.devices.Devices` | 4 | 4 | 0 |
| `org.sikuli.support.devices.Devices$TYPE` | 11 | 11 | 0 |
| `org.sikuli.support.devices.HelpDevice` | 13 | 13 | 0 |
| `org.sikuli.support.devices.IRobot` | 28 | 28 | 0 |
| `org.sikuli.support.devices.IRobot$KeyMode` | 11 | 11 | 0 |
| `org.sikuli.support.devices.IScreen` | 26 | 26 | 0 |
| `org.sikuli.support.devices.KeyboardLayout` | 2 | 2 | 0 |
| `org.sikuli.support.devices.MouseDevice` | 12 | 12 | 0 |
| `org.sikuli.support.devices.RobotDesktop` | 41 | 41 | 0 |
| `org.sikuli.support.devices.ScreenDevice` | 40 | 40 | 0 |
| `org.sikuli.support.gui.SXDialog` | 338 | 338 | 0 |
| `org.sikuli.support.gui.SXDialog$KEYS` | 11 | 11 | 0 |
| `org.sikuli.support.gui.SXDialog$POSITION` | 11 | 11 | 0 |
| `org.sikuli.support.recorder.PatternValidator` | 1 | 1 | 0 |
| `org.sikuli.support.recorder.PatternValidator$ValidationResult` | 0 | 0 | 0 |
| `org.sikuli.support.recorder.PatternValidator$Warning` | 11 | 11 | 0 |
| `org.sikuli.support.recorder.RecordedEventsFlow` | 4 | 4 | 0 |
| `org.sikuli.support.recorder.Recorder` | 12 | 12 | 0 |
| `org.sikuli.support.recorder.actions.ClickAction` | 5 | 5 | 0 |
| `org.sikuli.support.recorder.actions.DoubleClickAction` | 5 | 5 | 0 |
| `org.sikuli.support.recorder.actions.DragDropAction` | 1 | 1 | 0 |
| `org.sikuli.support.recorder.actions.IRecordedAction` | 1 | 1 | 0 |
| `org.sikuli.support.recorder.actions.MouseDownAction` | 3 | 3 | 0 |
| `org.sikuli.support.recorder.actions.MouseMoveAction` | 3 | 3 | 0 |
| `org.sikuli.support.recorder.actions.MouseUpAction` | 3 | 3 | 0 |
| `org.sikuli.support.recorder.actions.MouseWheelAction` | 3 | 3 | 0 |
| `org.sikuli.support.recorder.actions.PatternAction` | 3 | 3 | 0 |
| `org.sikuli.support.recorder.actions.RightClickAction` | 5 | 5 | 0 |
| `org.sikuli.support.recorder.actions.TypeKeyAction` | 1 | 1 | 0 |
| `org.sikuli.support.recorder.actions.TypeTextAction` | 1 | 1 | 0 |
| `org.sikuli.support.recorder.actions.WaitAction` | 3 | 3 | 0 |
| `org.sikuli.support.recorder.generators.ICodeGenerator` | 12 | 12 | 0 |
| `org.sikuli.support.recorder.generators.JavaCodeGenerator` | 12 | 12 | 0 |
| `org.sikuli.support.recorder.generators.JythonCodeGenerator` | 12 | 12 | 0 |
| `org.sikuli.support.recorder.generators.RobotFrameworkCodeGenerator` | 12 | 12 | 0 |
| `org.sikuli.support.runner.AbstractRunner` | 28 | 28 | 0 |
| `org.sikuli.support.runner.IRunner` | 22 | 22 | 0 |
| `org.sikuli.support.runner.IRunner$EffectiveRunner` | 4 | 4 | 0 |
| `org.sikuli.support.runner.IRunner$Options` | 13 | 13 | 0 |
| `org.sikuli.support.runner.ProcessRunner` | 34 | 34 | 0 |
| `org.sikuli.util.Crawler` | 1 | 1 | 0 |
| `org.sikuli.util.EventObserver` | 1 | 1 | 0 |
| `org.sikuli.util.EventSubject` | 2 | 2 | 0 |
| `org.sikuli.util.Highlight` | 331 | 331 | 0 |
| `org.sikuli.util.LinuxSupport` | 6 | 6 | 0 |
| `org.sikuli.util.OverlayCapturePrompt` | 339 | 339 | 0 |
| `org.sikuli.util.OverlayTransparentWindow` | 328 | 328 | 0 |
| `org.sikuli.util.Run` | 9 | 9 | 0 |
| `org.sikuli.util.SikulixFileChooser` | 8 | 8 | 0 |
| `org.sikuli.vnc.VNCScreen` | 314 | 314 | 0 |

## Python declarations absent from the Java class

These declarations need correction or removal; a dynamic call cannot make
a nonexistent Java method work. Constructors and private helpers are excluded.

- `org.sikuli.basics.Debug`: `is_`.
- `org.sikuli.guide.Tracker`: `yield_`.
- `org.sikuli.natives.mac.jna.ObjC`: `cls_`.
- `org.sikuli.script.Screen`: `as_`.

## Missing signatures in existing wrapper classes

Signatures below identify missing or incompatible declarations. Parameter
names are marked absent in the machine inventory when the Java artifact
was compiled without parameter-name metadata; `arg0` is not an original
source parameter name.

## Unregistered public Java classes

These classes still fall back to generic remote objects where reachable.
