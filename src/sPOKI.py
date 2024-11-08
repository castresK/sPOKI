import pygame
import os
import threading
import time
from tkinter import PhotoImage
from pymongo import MongoClient
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import customtkinter as ctk
import tkinter.simpledialog as simpledialog
from PIL import Image, ImageTk
import tkinter as tk


# Spotify API credentials
SPOTIFY_CLIENT_ID = "235b189daf3346fc9dbe5145cb64221c"
SPOTIFY_CLIENT_SECRET = "c609e3a2a85d46d2ae0e2940b31c433c"
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"
SCOPE = "user-modify-playback-state user-read-playback-state"

# Set up Spotipy with user authorization
try:
    sp = Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                                       client_secret=SPOTIFY_CLIENT_SECRET,
                                       redirect_uri=SPOTIFY_REDIRECT_URI,
                                       scope="user-modify-playback-state user-read-playback-state playlist-read-private playlist-read-collaborative"
))

except Exception as e:
    print(f"Error setting up Spotify client: {str(e)}")

# Connect to MongoDB
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["MusicPlayerDB"]
    collection = db["songs"]
except Exception as e:
    print(f"Error connecting to MongoDB: {str(e)}")

# Initialize Pygame mixer
pygame.mixer.init()

# Initialize variables
played_songs = []
search_history = []
playlist = []

# Main application window

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

root = ctk.CTk()
root.title("sPOKI")
root.geometry("500x600") 
root.resizable(False, False)  

root.configure(bg="#212121")

def search_song():
    dialog = ctk.CTkToplevel(root)
    dialog.title("Search Spotify")
    dialog.geometry("350x180")
    dialog.resizable(False, False) 

    dialog.configure(bg="#282c34")

    entry_label = ctk.CTkLabel(dialog, text="Enter song name:", font=("Poppins", 12, "bold"), text_color="white")
    entry_label.pack(pady=10)

    song_entry = ctk.CTkEntry(dialog, font=("Poppins", 12, "bold"))
    song_entry.pack(pady=5)

    def submit():
        song_name = song_entry.get()
        if song_name:
            try:
                results = sp.search(q=song_name, limit=1, type="track")
                if results['tracks']['items']:
                    track = results['tracks']['items'][0]
                    song_title = track['name']
                    artist_name = track['artists'][0]['name']
                    song_uri = track['uri']
                    song_label.configure(text=f"Found on Spotify: {song_title} by {artist_name}")

                    # Save the song metadata to MongoDB
                    song_data = {
                        "title": song_title,
                        "artist": artist_name,
                        "uri": song_uri,
                        "source": "Spotify"
                    }
                    collection.update_one({"uri": song_uri}, {"$set": song_data}, upsert=True)

                    play_song_on_spotify(song_uri)

                    # Update search history
                    if song_title not in search_history:
                        search_history.append(song_title)
                        add_to_history(song_title, artist_name) 
                else:
                    song_label.configure(text="Song not found on Spotify.")
            except Exception as e:
                song_label.configure(text=f"Error searching on Spotify: {str(e)}")
        
        dialog.destroy() 

    submit_button = ctk.CTkButton(dialog, text="Search", font=("Poppins", 12, "bold"), command=submit, hover_color="#1db954")
    submit_button.pack(pady=10)
    submit_button.configure(fg_color="#1db954")  

    cancel_button = ctk.CTkButton(dialog, text="Cancel", font=("Poppins", 12, "bold"), command=dialog.destroy, hover_color="#1db954")
    cancel_button.pack(pady=5)
    cancel_button.configure(fg_color="#1db954")  

def play_song_on_spotify(song_uri):
    try:
        devices = sp.devices()
        active_device = next((device for device in devices['devices'] if device['is_active']), None)

        if active_device:
            sp.start_playback(uris=[song_uri], device_id=active_device['id'])
            status_label.configure(text="Playing from Spotify.")
            
            threading.Thread(target=update_spotify_progress_bar).start()
        else:
            status_label.configure(text="No active device found. Please open the Spotify app on a device.")
    except Exception as e:
        status_label.configure(text=f"Error: {str(e)}")

def stop_song():
    pygame.mixer.music.stop()
    try:
        devices = sp.devices()
        active_device = next((device for device in devices['devices'] if device['is_active']), None)

        if active_device:
            sp.pause_playback()
            status_label.configure(text="Status: Paused")
        else:
            status_label.configure(text="No active device found. Please open the Spotify app on a device.")
    except Exception as e:
        status_label.configure(text=f"Error: {str(e)}")


def play_song_on_spotify(song_uri):
    try:
        devices = sp.devices()
        active_device = next((device for device in devices['devices'] if device['is_active']), None)

        if active_device:
            sp.start_playback(uris=[song_uri], device_id=active_device['id'])
            status_label.configure(text="Playing from Spotify.")
            
            threading.Thread(target=update_spotify_progress_bar).start()
        else:
            status_label.configure(text="No active device found. Please open the Spotify app on a device.")
    except Exception as e:
        status_label.configure(text=f"Error: {str(e)}")

def stop_song():
    pygame.mixer.music.stop()
    try:
        devices = sp.devices()
        active_device = next((device for device in devices['devices'] if device['is_active']), None)

        if active_device:
            sp.pause_playback()
            status_label.configure(text="Status: Paused")
        else:
            status_label.configure(text="No active device found. Please open the Spotify app on a device.")
    except Exception as e:
        status_label.configure(text=f"Error: {str(e)}")


# sporify playback
def update_spotify_progress_bar():
    try:
        while True:
            track_info = sp.current_playback()
            if track_info and track_info['is_playing']:
                duration = track_info['item']['duration_ms'] / 1000
                current_time = track_info['progress_ms'] / 1000
                progress_ratio = current_time / duration if duration else 0
                
                # Update progress bar on the main thread
                root.after(0, update_progress_bar, progress_ratio, current_time, duration)
                
                if current_time >= duration:  # Song is done, play the next song
                    play_next_song()
                    break

                time.sleep(1)
            else:
                break
    except Exception as e:
        print(f"Error updating Spotify progress bar: {str(e)}")

def play_next_song():
    """Play the next song in the playlist or history."""
    if playlist:
        next_song_uri = playlist.pop(0)  
        play_song_on_spotify(next_song_uri)
        status_label.configure(text="Playing next song...")
    elif search_history:
        song_name = search_history[0]  
        search_song_from_history(song_name)
        status_label.configure(text="Playing from search history...")
    else:
        status_label.configure(text="No more songs to play.")
    
    update_history_display()


def search_song_from_history(song_name):
    try:
        results = sp.search(q=song_name, limit=1, type="track")
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            song_title = track['name']
            artist_name = track['artists'][0]['name']
            song_uri = track['uri']
            song_label.configure(text=f"Found on Spotify: {song_title} by {artist_name}")
            
            play_song_on_spotify(song_uri)
            playlist.append(song_uri)  # Add to playlist to play next
        else:
            song_label.configure(text="Song not found on Spotify.")
    except Exception as e:
        song_label.configure(text=f"Error searching on Spotify: {str(e)}")

def update_progress_bar(progress_ratio, current_time, duration):
    progress_bar.set(progress_ratio)
    current_time_label.configure(text=f"{format_time(current_time)} / {format_time(duration)}")

def format_time(seconds):
    """Helper function to format time into MM:SS"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02}:{seconds:02}"

def toggle_play_pause():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()
        play_pause_button.configure(text="Play")
        status_label.configure(text="Status: Paused")
    else:
        pygame.mixer.music.unpause()
        play_pause_button.configure(text="Pause")
        status_label.configure(text="Status: Playing")

def pause_playback():
    try:
        devices = sp.devices()
        active_device = next((device for device in devices['devices'] if device['is_active']), None)

        if active_device:
            track_info = sp.current_playback()
            if track_info and track_info['is_playing']:
                sp.pause_playback(device_id=active_device['id'])
                status_label.configure(text="Status: Paused")
            else:
                status_label.configure(text="No track is currently playing.")
        else:
            status_label.configure(text="No active device found. Please open the Spotify app on a device.")
    except Exception as e:
        status_label.configure(text=f"Error: {str(e)}")


def pause_playback():
    try:
        devices = sp.devices()
        active_device = next((device for device in devices['devices'] if device['is_active']), None)

        if active_device:
            track_info = sp.current_playback()
            if track_info and track_info['is_playing']:
                sp.pause_playback(device_id=active_device['id'])
                status_label.configure(text="Status: Paused")
            else:
                status_label.configure(text="No track is currently playing.")
        else:
            status_label.configure(text="No active device found. Please open the Spotify app on a device.")
    except Exception as e:
        status_label.configure(text=f"Error: {str(e)}")

def show_playlists():
    dialog = ctk.CTkToplevel(root)
    dialog.title("Select a Playlist")
    dialog.geometry("350x300")
    dialog.resizable(False, False)
    dialog.configure(bg="#282c34")

    try:
        playlists = sp.current_user_playlists()
        if playlists['items']:
            scrollable_frame = ctk.CTkScrollableFrame(dialog, width=320, height=250, corner_radius=10)
            scrollable_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

            for playlist in playlists['items']:
                playlist_name = playlist['name']
                
                playlist_label = ctk.CTkLabel(scrollable_frame, text=playlist_name, font=("Poppins", 12), 
                                              text_color="white", anchor="w", padx=10, cursor="hand2")
                playlist_label.pack(fill="x", pady=5)

                # Event bindings for hover effect
                playlist_label.bind("<Enter>", lambda e, label=playlist_label: label.configure(text_color="#1db954"))
                playlist_label.bind("<Leave>", lambda e, label=playlist_label: label.configure(text_color="white"))

                # Attach event handler for clicking
                playlist_label.bind("<Button-1>", lambda e, uri=playlist['uri']: show_songs_from_playlist(uri))
                
        else:
            status_label.configure(text="No playlists found.")
    except Exception as e:
        status_label.configure(text=f"Error fetching playlists: {str(e)}")

def show_songs_from_playlist(playlist_uri):
    dialog = ctk.CTkToplevel(root)
    dialog.title("Select a Song from Playlist")
    dialog.geometry("350x300")
    dialog.resizable(False, False)
    dialog.configure(bg="#282c34")

    try:
        results = sp.playlist_tracks(playlist_uri)
        if results['items']:
            scrollable_frame = ctk.CTkScrollableFrame(dialog, width=320, height=250, corner_radius=10)
            scrollable_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

            for item in results['items']:
                song_name = item['track']['name']
                artist_name = item['track']['artists'][0]['name']
                
                song_label = ctk.CTkLabel(scrollable_frame, text=f"{song_name} by {artist_name}", font=("Poppins", 12),
                                          text_color="white", anchor="w", padx=10, cursor="hand2")
                song_label.pack(fill="x", pady=5)

                # Event bindings for hover effect
                song_label.bind("<Enter>", lambda e, label=song_label: label.configure(text_color="#1db954"))
                song_label.bind("<Leave>", lambda e, label=song_label: label.configure(text_color="white"))

                # Attach event handler for clicking
                song_label.bind("<Button-1>", lambda e, uri=item['track']['uri'], song_name=song_name, artist_name=artist_name: play_song_on_spotify(uri, song_name, artist_name))
        else:
            status_label.configure(text="No songs found in the playlist.")
    except Exception as e:
        status_label.configure(text=f"Error fetching songs: {str(e)}")

def play_song_on_spotify(song_uri, song_name, artist_name):
    try:
        devices = sp.devices()
        active_device = next((device for device in devices['devices'] if device['is_active']), None)

        if active_device:
            sp.start_playback(uris=[song_uri], device_id=active_device['id'])
            song_label.configure(text=f"Now Playing: {song_name} by {artist_name}")
            status_label.configure(text="Playing from Spotify.")
            
            if song_name not in played_songs:
                played_songs.append(song_name)
                add_to_history(song_name, artist_name)  
                
            threading.Thread(target=update_spotify_progress_bar).start()
        else:
            status_label.configure(text="No active device found. Please open the Spotify app on a device.")
    except Exception as e:
        status_label.configure(text=f"Error: {str(e)}")

# UI Elements
status_label = ctk.CTkLabel(root, text="Status: Idle", font=("Poppins", 12, "bold"))
status_label.pack(pady=10)

search_button = ctk.CTkButton(root, text="Search Song", font=("Poppins", 12, "bold"), command=search_song, hover_color="#1db954")
search_button.pack(pady=10)

playlist_button = ctk.CTkButton(root, text="Pick a Song from Playlist", font=("Poppins", 12, "bold"), command=show_playlists, hover_color="#1db954")
playlist_button.pack(pady=10, fill=ctk.X, padx=150)
playlist_button.configure(fg_color="#1db954")

play_pause_button = ctk.CTkButton(root, text="Play", command=toggle_play_pause, font=("Poppins", 12, "bold"), corner_radius=10, hover_color="#1db954")
play_pause_button.pack(pady=10, fill=ctk.X, padx=150)
play_pause_button.configure(fg_color="#1db954")  

stop_button = ctk.CTkButton(root, text="Stop", command=stop_song, font=("Poppins", 12, "bold"), corner_radius=10, hover_color="#1db954")
stop_button.pack(pady=10, fill=ctk.X, padx=150)
stop_button.configure(fg_color="#1db954")  

# Song title and artist labels
song_label = ctk.CTkLabel(root, text="No song loaded", font=("Poppins", 15, "bold"), wraplength=250, text_color="white")
song_label.pack(pady=10)

status_label = ctk.CTkLabel(root, text="Status: Stopped", font=("Poppins", 15), wraplength=250, text_color="white")
status_label.pack(pady=5)

# Volume Control
def set_volume(val):
    volume = float(val)
    pygame.mixer.music.set_volume(volume)
    try:
        active_device = sp.devices()['devices'][0]
        if active_device:
            sp.volume(int(volume * 100))
        volume_label.configure(text=f"Volume: {int(volume * 100)}%") 
    except Exception as e:
        print(f"Error setting volume on Spotify: {str(e)}")


volume_label = ctk.CTkLabel(root, text="Volume: 50%", font=("Poppins", 12), text_color="white")
volume_label.pack(pady=10)

volume_slider = ctk.CTkSlider(root, from_=0, to=1, command=set_volume, corner_radius=10)
volume_slider.set(0.5)
volume_slider.pack(pady=5, fill=ctk.X, padx=20)

pygame.mixer.music.set_volume(0.5)

# Display current track time and duration 
current_time_label = ctk.CTkLabel(root, text="00:00 / 00:00", font=("Poppins", 12), text_color="white")
current_time_label.pack(pady=1)

# Progress Bar
progress_bar = ctk.CTkProgressBar(root, corner_radius=10)
progress_bar.pack(pady=10, fill=ctk.X, padx=10)

# History Listbox
history_label = ctk.CTkLabel(root, text="Search History:", font=("Poppins", 12, "bold"), text_color="white")
history_label.pack(pady=5)

history_textbox = ctk.CTkTextbox(root, font=("Poppins", 12), corner_radius=10)
history_textbox.pack(pady=5, fill=ctk.BOTH, expand=True, padx=10)
history_textbox.configure(state="disabled")

#  add items to the history
def add_to_history(song_title, artist_name):
    history_textbox.configure(state="normal")  
    history_textbox.insert(ctk.END, f"{song_title} by {artist_name}\n")  
    history_textbox.configure(state="disabled")  

def update_history_display():
    history_textbox.configure(state="normal")
    history_textbox.delete(1.0, ctk.END)  
    for song in played_songs:
        history_textbox.insert(ctk.END, f"{song}\n")  
    history_textbox.configure(state="disabled")

root.mainloop()