import sqlite3

def insert_poster(movie_id, image_path):
    conn = sqlite3.connect("CinemaDB.db")
    cursor = conn.cursor()

    with open(image_path, "rb") as file:
        image_data = file.read()

    cursor.execute(
        """
        UPDATE Movies
        SET PosterImage = ?
        WHERE MovieID = ?
        """,
        (image_data, movie_id)
    )

    conn.commit()
    conn.close()

    print(f"Poster inserted for {movie_id}")


insert_poster("M001", "images/avengers.jpg")
insert_poster("M002", "images/shrek.jpg")
insert_poster("M003", "images/titanic.jpg")
insert_poster("M004", "images/lalaland.jpg")
insert_poster("M005", "images/harrypotter.jpg")