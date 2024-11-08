# sPOKI
Python App

# sPOKI- A Music Player Application

sPOKI is a Python-based music player application that integrates with Spotify and MongoDB for managing playlists and song history.

## Features
- Play music from Spotify
- Manage playlists
- View song history
- Store user preferences in MongoDB

## Setup Instructions

### Prerequisites
- Python 3.x
- MongoDB account (for using MongoDB)
- Spotify Developer Account (for accessing Spotify API)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/castresK/sPOKI.git
   cd sPOKI
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv spoki-env
   .\sPOKIt-env\Scripts\activate   # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up Spotify and MongoDB API keys as environment variables or in a `.env` file.

5. Run the application:
   ```bash
   python main.py
   ```

## Usage
After setting up, you can search for songs, create playlists, and play music directly from Spotify.

