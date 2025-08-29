import pyttsx3

engine = pyttsx3.init()
engine.save_to_file("Hello world, this is a test from pyttsx3.", "C:\\Users\\Reign\\Documents\\Python Projects\\VibeType\\test.wav")
engine.runAndWait()
