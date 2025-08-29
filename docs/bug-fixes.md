okay cool but what happened to the system tray icon and why do we still have this
tk window that's blank opening up all the time the window title tk on top of
our settings window there's another window, Also, currently I don't yet as happy working at all.
Can we add a toggle to turn it on and off in the settings?
I don't want my dictation to be read back to me every single time.
I want the option to turn it off.

also the mic selection and mic test and audio output so the speech test whether
it's level indicator and the mic test with this level indicator and the mic
selector are all missing we needed this screen for audio and audio outputs and audio
inputs with the volume bars or sound level bars.

I've also been thinking about hotkeys, and I think that
out-control E should be for the LLM to explain.
The highlighted and selected text.
Out-control and R should be for dictation, for it to read to me.
And out-control T should be for me to be able to
talk to the LLM, essentially kind of like what
scroll lock does.

Instructions for VibeType (Speech-to-Text / Text-to-Speech LLM Assistant)

System Tray & Windows

The application should only show the main settings window when explicitly opened.

Currently, an extra blank Tkinter window (titled “tk”) is appearing — this must be removed.

The system tray icon should be properly integrated so the app can run in the background without unnecessary windows.

Text-to-Speech (TTS) Toggle

Add a toggle in the settings window to enable/disable automatic TTS playback.

When disabled, dictation is transcribed but not read aloud.

This gives the user control over when text is spoken back.

Audio Settings Screen

Add an Audio I/O configuration page in settings that includes:

Microphone selector (dropdown of available input devices).

Microphone level indicator (real-time volume bar for mic input).

Test microphone button (plays back test recording).

Speaker/output device selector (dropdown of output devices).

Speaker test button (plays a short sound to confirm output works).

Hotkey System

Define the following global hotkeys:

Alt + Ctrl + E → LLM explains the highlighted/selected text.

Alt + Ctrl + R → LLM reads the highlighted/selected text aloud (TTS).

Alt + Ctrl + T → Start voice conversation with the LLM (push-to-talk style, similar to Scroll Lock toggling).

✅ Deliverables:

No extra blank Tk window.

Working system tray icon.

Toggle to enable/disable automatic TTS playback.

Audio input/output selection with mic test + level indicators.

Hotkeys integrated with defined functions.