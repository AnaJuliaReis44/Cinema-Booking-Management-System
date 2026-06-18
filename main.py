import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

DB_NAME = "CinemaDB.db"


def connect_db():
    return sqlite3.connect(DB_NAME)


def load_movies():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT MovieID, Title, Genre
        FROM Movies
    """)

    rows = cursor.fetchall()
    conn.close()
    return rows


def show_movies():
    for row in movie_table.get_children():
        movie_table.delete(row)

    for movie in load_movies():
        movie_table.insert("", tk.END, values=movie)


root = tk.Tk()
root.title("Cinema Booking Management System")
root.geometry("750x450")

title_label = tk.Label(
    root,
    text="Cinema Booking Management System",
    font=("Arial", 18, "bold")
)
title_label.pack(pady=10)

movie_table = ttk.Treeview(
    root,
    columns=("MovieID", "Title", "Genre"),
    show="headings"
)

movie_table.heading("MovieID", text="Movie ID")
movie_table.heading("Title", text="Title")
movie_table.heading("Genre", text="Genre")

movie_table.pack(fill="both", expand=True, padx=20, pady=10)

load_button = tk.Button(
    root,
    text="Load Movies",
    command=show_movies
)
load_button.pack(pady=10)

root.mainloop()