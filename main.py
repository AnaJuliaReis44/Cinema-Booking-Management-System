import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import base64
import uuid

DB_NAME = "CinemaDB.db"
selected_movie_id = None
selected_showtime_id = None
selected_seats = []


def connect_db():
    return sqlite3.connect(DB_NAME)


def fetch_data(query, params=()):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as error:
        messagebox.showerror("Database Error", str(error))
        return []


def execute_query(query, params=()):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as error:
        messagebox.showerror("Database Error", str(error))
        return False


def load_table(tree, query, params=()):
    for row in tree.get_children():
        tree.delete(row)

    for record in fetch_data(query, params):
        tree.insert("", tk.END, values=record)


def create_table(parent, columns):
    tree = ttk.Treeview(parent, columns=columns, show="headings")

    for column in columns:
        tree.heading(column, text=column)
        tree.column(column, width=120)

    tree.pack(fill="both", expand=True, padx=20, pady=20)
    return tree


def calculate_discount(ticket_price, seats_count, show_time):
    total = ticket_price * seats_count

    offers = fetch_data("SELECT OfferName, DiscountPercent, IsEnabled FROM SpecialOffers")

    morning_enabled = False
    group_enabled = False
    morning_discount = 0
    group_discount = 0

    for offer in offers:
        if offer[0] == "Morning Discount" and offer[2] == 1:
            morning_enabled = True
            morning_discount = offer[1]
        if offer[0] == "Group Booking Discount" and offer[2] == 1:
            group_enabled = True
            group_discount = offer[1]

    if morning_enabled and show_time < "12:00":
        total = total - (total * morning_discount / 100)

    if group_enabled and seats_count >= 3:
        total = total - (total * group_discount / 100)

    return round(total, 2)


root = tk.Tk()
root.title("Cinema Booking Management System")
root.geometry("1250x800")

title_label = tk.Label(
    root,
    text="Cinema Booking Management System",
    font=("Arial", 20, "bold")
)
title_label.pack(pady=10)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=20, pady=20)

customer_tab = ttk.Frame(notebook)
admin_tab = ttk.Frame(notebook)
data_tab = ttk.Frame(notebook)

notebook.add(customer_tab, text="Customer Booking")
notebook.add(admin_tab, text="Admin")
notebook.add(data_tab, text="Data Overview")

# ---------------- CUSTOMER TAB ----------------

search_frame = tk.LabelFrame(customer_tab, text="Film Search")
search_frame.pack(fill="x", padx=10, pady=10)

tk.Label(search_frame, text="Search by Title:").grid(row=0, column=0, padx=5, pady=5)
title_search_entry = tk.Entry(search_frame, width=25)
title_search_entry.grid(row=0, column=1, padx=5)

tk.Label(search_frame, text="Search by Genre:").grid(row=0, column=2, padx=5, pady=5)
genre_search_entry = tk.Entry(search_frame, width=25)
genre_search_entry.grid(row=0, column=3, padx=5)

movies_tree = create_table(
    customer_tab,
    ("MovieID", "Title", "Genre", "AgeRating", "DurationMinutes")
)

screenings_tree = create_table(
    customer_tab,
    ("ShowtimeID", "MovieTitle", "Hall", "ShowDate", "ShowTime", "TicketPrice")
)

seat_frame = tk.LabelFrame(customer_tab, text="Seat Selection")
seat_frame.pack(fill="x", padx=10, pady=10)


def load_all_movies():
    load_table(
        movies_tree,
        """
        SELECT MovieID, Title, Genre, AgeRating, DurationMinutes
        FROM Movies
        """
    )


def search_by_title():
    keyword = title_search_entry.get()
    load_table(
        movies_tree,
        """
        SELECT MovieID, Title, Genre, AgeRating, DurationMinutes
        FROM Movies
        WHERE Title LIKE ?
        """,
        (f"%{keyword}%",)
    )


def search_by_genre():
    keyword = genre_search_entry.get()
    load_table(
        movies_tree,
        """
        SELECT MovieID, Title, Genre, AgeRating, DurationMinutes
        FROM Movies
        WHERE Genre LIKE ?
        """,
        (f"%{keyword}%",)
    )


def select_movie(event):
    global selected_movie_id

    selected = movies_tree.focus()
    if not selected:
        return

    values = movies_tree.item(selected, "values")
    selected_movie_id = values[0]

    load_table(
        screenings_tree,
        """
        SELECT
            s.ShowtimeID,
            m.Title,
            sc.ScreenName,
            s.ShowDate,
            s.ShowTime,
            s.TicketPrice
        FROM Showtimes s
        JOIN Movies m ON s.MovieID = m.MovieID
        JOIN Screens sc ON s.ScreenID = sc.ScreenID
        WHERE m.MovieID = ?
        """,
        (selected_movie_id,)
    )


def select_screening(event):
    global selected_showtime_id, selected_seats

    selected = screenings_tree.focus()
    if not selected:
        return

    values = screenings_tree.item(selected, "values")
    selected_showtime_id = values[0]
    selected_seats = []

    for widget in seat_frame.winfo_children():
        widget.destroy()

    seats = fetch_data(
        """
        SELECT SeatNumber, IsAvailable
        FROM Seats
        WHERE ShowtimeID = ?
        ORDER BY SeatNumber
        """,
        (selected_showtime_id,)
    )

    if not seats:
        tk.Label(seat_frame, text="No seats found for this screening.").pack()
        return

    def toggle_seat(button, seat_number):
        if seat_number in selected_seats:
            selected_seats.remove(seat_number)
            button.config(relief="raised")
        else:
            selected_seats.append(seat_number)
            button.config(relief="sunken")

    row = 0
    col = 0

    for seat_number, is_available in seats:
        btn = tk.Button(
            seat_frame,
            text=f"Seat {seat_number}",
            width=10
        )

        if is_available == 0:
            btn.config(state="disabled", text=f"Seat {seat_number}\nBooked")
        else:
            btn.config(command=lambda b=btn, s=seat_number: toggle_seat(b, s))

        btn.grid(row=row, column=col, padx=5, pady=5)

        col += 1
        if col == 6:
            col = 0
            row += 1


def purchase_ticket():
    if not selected_showtime_id:
        messagebox.showwarning("Missing Selection", "Please select a screening.")
        return

    if not selected_seats:
        messagebox.showwarning("Missing Selection", "Please select at least one seat.")
        return

    customer_id = simpledialog.askstring("Customer", "Enter Customer ID:")
    if not customer_id:
        return

    customer_exists = fetch_data(
        "SELECT CustomerID FROM Customers WHERE CustomerID = ?",
        (customer_id,)
    )

    if not customer_exists:
        messagebox.showerror("Customer Error", "Customer ID does not exist.")
        return

    showtime = fetch_data(
        """
        SELECT m.Title, s.ShowDate, s.ShowTime, s.TicketPrice
        FROM Showtimes s
        JOIN Movies m ON s.MovieID = m.MovieID
        WHERE s.ShowtimeID = ?
        """,
        (selected_showtime_id,)
    )[0]

    film_title, show_date, show_time, ticket_price = showtime
    total_price = calculate_discount(ticket_price, len(selected_seats), show_time)

    payment_amount = simpledialog.askfloat(
        "Payment",
        f"Total price is £{total_price:.2f}. Enter payment amount:"
    )

    if payment_amount is None:
        return

    if payment_amount < total_price:
        messagebox.showerror("Payment Failed", "Insufficient payment. Transaction refused.")
        return

    booking_id = "B" + str(uuid.uuid4())[:6].upper()
    payment_id = "P" + str(uuid.uuid4())[:6].upper()

    seats_text = ",".join(str(seat) for seat in selected_seats)

    success = execute_query(
        """
        INSERT INTO Bookings
        (BookingID, CustomerID, ShowtimeID, StaffID, SeatsBooked, TotalAmount, BookingStatus)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (booking_id, customer_id, selected_showtime_id, "ST001", len(selected_seats), total_price, "Confirmed")
    )

    if not success:
        return

    execute_query(
        """
        INSERT INTO Payments
        (PaymentID, BookingID, PaymentMethod, PaymentStatus, PaymentDate, Amount)
        VALUES (?, ?, ?, ?, date('now'), ?)
        """,
        (payment_id, booking_id, "Virtual Payment", "Paid", total_price)
    )

    for seat in selected_seats:
        execute_query(
            """
            UPDATE Seats
            SET IsAvailable = 0
            WHERE ShowtimeID = ? AND SeatNumber = ?
            """,
            (selected_showtime_id, seat)
        )

    ticket = f"""
*******************************
CINEMARK
Film: {film_title}
Date: {show_date}
Time: {show_time}
Seats: {seats_text}
Price: £{total_price:.2f}
*******************************
"""

    messagebox.showinfo("Ticket", ticket)

    load_bookings_data()
    select_screening(None)


movies_tree.bind("<<TreeviewSelect>>", select_movie)
screenings_tree.bind("<<TreeviewSelect>>", select_screening)

customer_button_frame = tk.Frame(customer_tab)
customer_button_frame.pack(pady=10)

tk.Button(customer_button_frame, text="Search Title", command=search_by_title, width=15).grid(row=0, column=0, padx=5)
tk.Button(customer_button_frame, text="Search Genre", command=search_by_genre, width=15).grid(row=0, column=1, padx=5)
tk.Button(customer_button_frame, text="Load All Films", command=load_all_movies, width=15).grid(row=0, column=2, padx=5)
tk.Button(customer_button_frame, text="Purchase Ticket", command=purchase_ticket, width=15).grid(row=0, column=3, padx=5)

# ---------------- ADMIN TAB ----------------

admin_logged_in = False

login_frame = tk.LabelFrame(admin_tab, text="Administrator Login")
login_frame.pack(fill="x", padx=10, pady=10)

tk.Label(login_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5)
admin_username_entry = tk.Entry(login_frame, width=25)
admin_username_entry.grid(row=0, column=1, padx=5)

tk.Label(login_frame, text="Password:").grid(row=0, column=2, padx=5, pady=5)
admin_password_entry = tk.Entry(login_frame, width=25, show="*")
admin_password_entry.grid(row=0, column=3, padx=5)

admin_controls = tk.LabelFrame(admin_tab, text="Admin Controls")
admin_controls.pack(fill="x", padx=10, pady=10)
admin_offer_tree = create_table(
    admin_tab,
    ("OfferID", "OfferName", "DiscountPercent", "Status")
)

def admin_login():
    global admin_logged_in

    username = admin_username_entry.get()
    password = admin_password_entry.get()

    result = fetch_data(
        """
        SELECT PasswordEncrypted
        FROM UserLogin
        WHERE Username = ?
        """,
        (username,)
    )

    if not result:
        messagebox.showerror("Login Failed", "Invalid username.")
        return

    encrypted_password = result[0][0]

    try:
        decoded_password = base64.b64decode(encrypted_password).decode("utf-8")
    except Exception:
        decoded_password = encrypted_password

    if password == decoded_password:
        admin_logged_in = True
        messagebox.showinfo("Login Successful", "Administrator access granted.")
    else:
        messagebox.showerror("Login Failed", "Incorrect password.")


def require_admin():
    if not admin_logged_in:
        messagebox.showwarning("Access Denied", "Please login as administrator first.")
        return False
    return True


def modify_price():
    if not require_admin():
        return

    movie_id = simpledialog.askstring("Modify Price", "Enter Movie ID:")
    factor = simpledialog.askfloat("Modify Price", "Enter price factor percentage (e.g. 10 or -10):")

    if not movie_id or factor is None:
        return

    execute_query(
        """
        UPDATE Showtimes
        SET TicketPrice = ROUND(TicketPrice * (1 + ? / 100), 2)
        WHERE MovieID = ?
        """,
        (factor, movie_id)
    )

    messagebox.showinfo("Success", "Ticket prices updated.")
    load_all_data()

def edit_film():
    if not require_admin():
        return

    movie_id = simpledialog.askstring("Edit Film", "Enter Movie ID to edit:")
    if not movie_id:
        return

    movie = fetch_data(
        "SELECT Title, Genre, AgeRating, DurationMinutes FROM Movies WHERE MovieID = ?",
        (movie_id,)
    )

    if not movie:
        messagebox.showerror("Error", "Movie not found.")
        return

    current_title, current_genre, current_age, current_duration = movie[0]

    new_title = simpledialog.askstring("Edit Film", "Enter new title:", initialvalue=current_title)
    new_genre = simpledialog.askstring("Edit Film", "Enter new genre:", initialvalue=current_genre)
    new_age = simpledialog.askstring("Edit Film", "Enter new age rating:", initialvalue=current_age)
    new_duration = simpledialog.askinteger("Edit Film", "Enter new duration:", initialvalue=current_duration)

    if not all([new_title, new_genre, new_age, new_duration]):
        return

    execute_query(
        """
        UPDATE Movies
        SET Title = ?, Genre = ?, AgeRating = ?, DurationMinutes = ?
        WHERE MovieID = ?
        """,
        (new_title, new_genre, new_age, new_duration, movie_id)
    )

    showtimes = fetch_data(
        """
        SELECT ShowtimeID, ShowDate, ShowTime, TicketPrice
        FROM Showtimes
        WHERE MovieID = ?
        """,
        (movie_id,)
    )

    if showtimes:
        showtime_id = simpledialog.askstring(
            "Edit Screening",
            "Enter Showtime ID to edit:"
        )

        selected_showtime = None

        for showtime in showtimes:
            if showtime[0] == showtime_id:
                selected_showtime = showtime
                break

        if selected_showtime:
            current_showtime_id, current_date, current_time, current_price = selected_showtime

            new_date = simpledialog.askstring(
                "Edit Screening",
                "Enter new show date:",
                initialvalue=current_date
            )

            new_time = simpledialog.askstring(
                "Edit Screening",
                "Enter new show time:",
                initialvalue=current_time
            )

            new_price = simpledialog.askfloat(
                "Edit Screening",
                "Enter new ticket price:",
                initialvalue=current_price
            )

            if new_date and new_time and new_price is not None:
                execute_query(
                    """
                    UPDATE Showtimes
                    SET ShowDate = ?, ShowTime = ?, TicketPrice = ?
                    WHERE ShowtimeID = ?
                    """,
                    (new_date, new_time, new_price, current_showtime_id)
                )

    messagebox.showinfo("Success", "Film and screening updated successfully.")
    load_all_data()
    load_all_movies()

def delete_film():
    if not require_admin():
        return

    movie_id = simpledialog.askstring("Delete Film", "Enter Movie ID to delete:")
    if not movie_id:
        return

    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Are you sure you want to delete movie {movie_id}?"
    )

    if not confirm:
        return

    showtimes = fetch_data(
        "SELECT ShowtimeID FROM Showtimes WHERE MovieID = ?",
        (movie_id,)
    )

    if not showtimes:
        messagebox.showerror("Error", "Movie not found or has no screenings.")
        return

    for showtime in showtimes:
        showtime_id = showtime[0]

        bookings = fetch_data(
            "SELECT BookingID FROM Bookings WHERE ShowtimeID = ?",
            (showtime_id,)
        )

        for booking in bookings:
            booking_id = booking[0]
            execute_query("DELETE FROM Payments WHERE BookingID = ?", (booking_id,))
            execute_query("DELETE FROM Bookings WHERE BookingID = ?", (booking_id,))

        execute_query("DELETE FROM Seats WHERE ShowtimeID = ?", (showtime_id,))
        execute_query("DELETE FROM Showtimes WHERE ShowtimeID = ?", (showtime_id,))

    execute_query("DELETE FROM Movies WHERE MovieID = ?", (movie_id,))

    messagebox.showinfo("Success", "Film deleted successfully.")
    load_all_data()
    load_all_movies()


def add_film():
    if not require_admin():
        return

    movie_id = simpledialog.askstring("New Film", "Enter Movie ID:")
    title = simpledialog.askstring("New Film", "Enter film title:")
    genre = simpledialog.askstring("New Film", "Enter genre:")
    age_rating = simpledialog.askstring("New Film", "Enter age rating:")
    duration = simpledialog.askinteger("New Film", "Enter duration in minutes:")

    showtime_id = simpledialog.askstring("Screening", "Enter Showtime ID:")
    screen_id = simpledialog.askstring("Screening", "Enter Screen ID:")
    show_date = simpledialog.askstring("Screening", "Enter show date:")
    show_time = simpledialog.askstring("Screening", "Enter show time:")
    price = simpledialog.askfloat("Screening", "Enter ticket price:")

    if not all([movie_id, title, genre, age_rating, duration, showtime_id, screen_id, show_date, show_time, price]):
        return

    execute_query(
        """
        INSERT INTO Movies
        (MovieID, Title, Genre, AgeRating, DurationMinutes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (movie_id, title, genre, age_rating, duration)
    )

    execute_query(
        """
        INSERT INTO Showtimes
        (ShowtimeID, MovieID, ScreenID, ShowDate, ShowTime, TicketPrice)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (showtime_id, movie_id, screen_id, show_date, show_time, price)
    )

    for seat in range(1, 13):
        execute_query(
            """
            INSERT INTO Seats
            VALUES (?, ?, ?, 1)
            """,
            (f"{showtime_id}_S{seat}", showtime_id, seat)
        )

    messagebox.showinfo("Success", "Film and screening added.")
    load_all_data()


def toggle_offer():
    if not require_admin():
        return

    offer_id = simpledialog.askstring("Special Offer", "Enter Offer ID (O001 or O002):")
    if not offer_id:
        return

    current = fetch_data(
        "SELECT IsEnabled FROM SpecialOffers WHERE OfferID = ?",
        (offer_id,)
    )

    if not current:
        messagebox.showerror("Error", "Offer not found.")
        return

    new_status = 0 if current[0][0] == 1 else 1

    execute_query(
        """
        UPDATE SpecialOffers
        SET IsEnabled = ?
        WHERE OfferID = ?
        """,
        (new_status, offer_id)
    )

    messagebox.showinfo("Success", "Offer status updated.")
    load_offers_data()


tk.Button(login_frame, text="Login", command=admin_login, width=15).grid(row=0, column=4, padx=5)

tk.Button(admin_controls, text="Add Film", command=add_film, width=20).grid(row=0, column=0, padx=5, pady=5)
tk.Button(admin_controls, text="Edit Film", command=edit_film, width=20).grid(row=0, column=1, padx=5, pady=5)
tk.Button(admin_controls, text="Delete Film", command=delete_film, width=20).grid(row=0, column=2, padx=5, pady=5)
tk.Button(admin_controls, text="Modify Prices", command=modify_price, width=20).grid(row=0, column=3, padx=5, pady=5)
tk.Button(admin_controls, text="Enable/Disable Offer", command=toggle_offer, width=20).grid(row=0, column=4, padx=5, pady=5)

# ---------------- DATA OVERVIEW TAB ----------------

data_notebook = ttk.Notebook(data_tab)
data_notebook.pack(fill="both", expand=True)

movies_data_tab = ttk.Frame(data_notebook)
customers_data_tab = ttk.Frame(data_notebook)
bookings_data_tab = ttk.Frame(data_notebook)
offers_data_tab = ttk.Frame(data_notebook)

data_notebook.add(movies_data_tab, text="Movies")
data_notebook.add(customers_data_tab, text="Customers")
data_notebook.add(bookings_data_tab, text="Bookings")
data_notebook.add(offers_data_tab, text="Offers")

movies_data_tree = create_table(
    movies_data_tab,
    ("MovieID", "Title", "Genre", "AgeRating", "DurationMinutes")
)

customers_data_tree = create_table(
    customers_data_tab,
    ("CustomerID", "FirstName", "LastName", "Email", "Phone")
)

bookings_data_tree = create_table(
    bookings_data_tab,
    ("BookingID", "CustomerName", "MovieTitle", "ShowDate", "ShowTime", "SeatsBooked", "TotalAmount", "BookingStatus")
)

offers_data_tree = create_table(
    offers_data_tab,
    ("OfferID", "OfferName", "DiscountPercent", "IsEnabled")
)


def load_movies_data():
    load_table(
        movies_data_tree,
        """
        SELECT MovieID, Title, Genre, AgeRating, DurationMinutes
        FROM Movies
        """
    )


def load_customers_data():
    load_table(
        customers_data_tree,
        """
        SELECT CustomerID, FirstName, LastName, Email, Phone
        FROM Customers
        """
    )


def load_bookings_data():
    load_table(
        bookings_data_tree,
        """
        SELECT
            b.BookingID,
            c.FirstName || ' ' || c.LastName,
            m.Title,
            s.ShowDate,
            s.ShowTime,
            b.SeatsBooked,
            b.TotalAmount,
            b.BookingStatus
        FROM Bookings b
        JOIN Customers c ON b.CustomerID = c.CustomerID
        JOIN Showtimes s ON b.ShowtimeID = s.ShowtimeID
        JOIN Movies m ON s.MovieID = m.MovieID
        """
    )


def load_offers_data():
    load_table(
        offers_data_tree,
        """
        SELECT
            OfferID,
            OfferName,
            DiscountPercent,
            CASE
                WHEN IsEnabled = 1 THEN 'ON'
                ELSE 'OFF'
            END AS Status
        FROM SpecialOffers
        """
    )

    load_table(
        admin_offer_tree,
        """
        SELECT
            OfferID,
            OfferName,
            DiscountPercent,
            CASE
                WHEN IsEnabled = 1 THEN 'ON'
                ELSE 'OFF'
            END AS Status
        FROM SpecialOffers
        """
    )


def load_all_data():
    load_all_movies()
    load_movies_data()
    load_customers_data()
    load_bookings_data()
    load_offers_data()


refresh_frame = tk.Frame(data_tab)
refresh_frame.pack(pady=10)

tk.Button(refresh_frame, text="Refresh All Data", command=load_all_data, width=20).pack()

load_all_data()

root.mainloop()