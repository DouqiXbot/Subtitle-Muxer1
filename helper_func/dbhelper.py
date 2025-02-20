import sqlite3
from typing import Optional, Dict, Any

class Database:
    """A SQLite database handler for managing muxbot user data."""

    def __init__(self, db_path: str = "muxdb.sqlite"):
        """
        Initialize the database connection.
        
        Args:
            db_path (str): Path to the SQLite database file. Defaults to 'muxdb.sqlite'.
        """
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return results as dictionaries
        self.setup()

    def setup(self) -> None:
        """Set up the database table if it doesn't exist."""
        cmd = """
        CREATE TABLE IF NOT EXISTS muxbot (
            user_id INTEGER PRIMARY KEY,
            vid_name TEXT,
            sub_name TEXT,
            filename TEXT,
            encoding_settings TEXT  -- Store JSON-like string for settings
        );
        """
        try:
            self.conn.execute(cmd)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error setting up database: {e}")

    def _execute_query(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """
        Execute a query and return the first result.
        
        Args:
            query (str): SQL query to execute.
            params (tuple): Parameters to prevent SQL injection.
        
        Returns:
            Optional[sqlite3.Row]: Result row or None if no result.
        """
        try:
            cursor = self.conn.execute(query, params)
            return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Query error: {e}")
            return None

    def put_video(self, user_id: int, vid_name: str, filename: str) -> bool:
        """
        Store or update video filename for a user.
        
        Args:
            user_id (int): User's Telegram ID.
            vid_name (str): Video filename.
            filename (str): Final output filename.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        res = self._execute_query("SELECT * FROM muxbot WHERE user_id = ?", (user_id,))
        if res:
            query = "UPDATE muxbot SET vid_name = ?, filename = ? WHERE user_id = ?"
            params = (vid_name, filename, user_id)
        else:
            query = "INSERT INTO muxbot (user_id, vid_name, filename) VALUES (?, ?, ?)"
            params = (user_id, vid_name, filename)
        
        try:
            self.conn.execute(query, params)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error storing video: {e}")
            return False

    def put_sub(self, user_id: int, sub_name: str) -> bool:
        """Store or update subtitle filename for a user."""
        res = self._execute_query("SELECT * FROM muxbot WHERE user_id = ?", (user_id,))
        if res:
            query = "UPDATE muxbot SET sub_name = ? WHERE user_id = ?"
            params = (sub_name, user_id)
        else:
            query = "INSERT INTO muxbot (user_id, sub_name) VALUES (?, ?)"
            params = (user_id, sub_name)
        
        try:
            self.conn.execute(query, params)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error storing subtitle: {e}")
            return False

    def check_sub(self, user_id: int) -> bool:
        """Check if a subtitle file exists for the user."""
        res = self._execute_query("SELECT sub_name FROM muxbot WHERE user_id = ?", (user_id,))
        return bool(res and res["sub_name"])

    def check_video(self, user_id: int) -> bool:
        """Check if a video file exists for the user."""
        res = self._execute_query("SELECT vid_name FROM muxbot WHERE user_id = ?", (user_id,))
        return bool(res and res["vid_name"])

    def get_vid_filename(self, user_id: int) -> Optional[str]:
        """Get the video filename for a user."""
        res = self._execute_query("SELECT vid_name FROM muxbot WHERE user_id = ?", (user_id,))
        return res["vid_name"] if res else None

    def get_sub_filename(self, user_id: int) -> Optional[str]:
        """Get the subtitle filename for a user."""
        res = self._execute_query("SELECT sub_name FROM muxbot WHERE user_id = ?", (user_id,))
        return res["sub_name"] if res else None

    def get_filename(self, user_id: int) -> Optional[str]:
        """Get the final filename for a user."""
        res = self._execute_query("SELECT filename FROM muxbot WHERE user_id = ?", (user_id,))
        return res["filename"] if res else None

    def set_encoding_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """Store encoding settings for a user as a JSON string."""
        import json
        settings_str = json.dumps(settings)
        res = self._execute_query("SELECT * FROM muxbot WHERE user_id = ?", (user_id,))
        if res:
            query = "UPDATE muxbot SET encoding_settings = ? WHERE user_id = ?"
            params = (settings_str, user_id)
        else:
            query = "INSERT INTO muxbot (user_id, encoding_settings) VALUES (?, ?)"
            params = (user_id, settings_str)
        
        try:
            self.conn.execute(query, params)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error storing settings: {e}")
            return False

    def get_encoding_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get encoding settings for a user."""
        import json
        res = self._execute_query("SELECT encoding_settings FROM muxbot WHERE user_id = ?", (user_id,))
        if res and res["encoding_settings"]:
            return json.loads(res["encoding_settings"])
        return None

    def erase(self, user_id: int) -> bool:
        """Delete all data for a user."""
        try:
            self.conn.execute("DELETE FROM muxbot WHERE user_id = ?", (user_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error erasing data: {e}")
            return False

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

if __name__ == "__main__":
    # Example usage
    db = Database()
    db.put_video(123, "video.mp4", "output.mp4")
    db.put_sub(123, "subs.srt")
    db.set_encoding_settings(123, {"crf": "20", "preset": "superfast"})
    print(db.get_vid_filename(123))  # Output: video.mp4
    print(db.get_encoding_settings(123))  # Output: {'crf': '20', 'preset': 'superfast'}
    db.erase(123)
    db.close()
