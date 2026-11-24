import random
import string

import mysql.connector as db


def connect_database():
    return db.connect(
        user="root",
        password="vighnesh21V",
        host="localhost",
        database="train_reservation",
    )


def generate_pnr():
    letters = "".join(random.choice(string.ascii_uppercase) for _ in range(3))
    numbers = "".join(random.choice(string.digits) for _ in range(7))
    return letters + numbers


def search_trains(cursor):
    source = input("Enter source: ").strip()
    destination = input("Enter destination: ").strip()

    cursor.execute(
        """
        SELECT t.train_id, t.train_no, t.train_name, t.source, t.destination, t.distance,
               s.schedule_id, s.departure_time, s.arrival_time, s.day_number
        FROM trains AS t
        JOIN schedules AS s ON s.train_id = t.train_id
        WHERE LOWER(t.source) = LOWER(%s)
          AND LOWER(t.destination) = LOWER(%s)
        """,
        (source, destination),
    )
    trains = cursor.fetchall()

    if not trains:
        print("No trains found for this route.")
        return

    print("\nAvailable trains:")
    print("-" * 75)
    for train in trains:
        print(
            f"Schedule ID: {train['schedule_id']} | "
            f"{train['train_name']} ({train['train_id']}) | "
            f"{train['source']} -> {train['destination']} | "
            f"Departure: {train['departure_time']} | "
            f"Arrival: {train['arrival_time']}"
        )


def book_ticket(cursor, connection):
    schedule_id = int(input("Enter schedule ID: ").strip())
    passenger_count = int(input("Enter number of passengers: ").strip())

    cursor.execute(
        "SELECT schedule_id, train_id FROM schedules WHERE schedule_id = %s",
        (schedule_id,),
    )
    schedule = cursor.fetchone()
    if not schedule:
        print("Invalid schedule ID.")
        return

    cursor.execute(
        """
        SELECT seat_id, seat_no, class_type
        FROM seats
        WHERE schedule_id = %s AND LOWER(status) = 'available'
        LIMIT %s
        """,
        (schedule_id, passenger_count),
    )
    available_seats = cursor.fetchall()

    if len(available_seats) < passenger_count:
        print("Not enough seats available.")
        return

    passengers = []
    for number in range(1, passenger_count + 1):
        print(f"\nPassenger {number}")
        name = input("Name: ").strip()
        age = int(input("Age: ").strip())
        gender = input("Gender (M/F/O): ").strip().upper()
        berth_preference = input("Berth preference: ").strip()
        passengers.append((name, age, gender, berth_preference))

    pnr = generate_pnr()
    total_amount = passenger_count * 500

    try:
        cursor.execute(
            """
            INSERT INTO bookings
            (pnr, user_id, schedule_id, total_amount, status)
            VALUES (%s, %s, %s, %s, 'Confirmed')
            """,
            (
                pnr,
                1,
                schedule_id,
                total_amount,
            ),
        )
        booking_id = cursor.lastrowid

        for passenger, seat in zip(passengers, available_seats):
            cursor.execute(
                """
                INSERT INTO passengers
                (booking_id, name, age, gender, berth_preference)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (booking_id, *passenger),
            )
            cursor.execute(
                "UPDATE seats SET status = 'Booked' WHERE seat_id = %s",
                (seat["seat_id"],),
            )

        connection.commit()
        print(f"\nTicket booked successfully.")
        print(f"PNR: {pnr}")
        print(f"Booking ID: {booking_id}")
        print(f"Total amount: Rs.{total_amount}")
    except db.Error as error:
        connection.rollback()
        print(f"Booking failed: {error}")


def cancel_ticket(cursor, connection):
    pnr = input("Enter PNR: ").strip().upper()

    cursor.execute(
        "SELECT booking_id, schedule_id, status FROM bookings WHERE pnr = %s",
        (pnr,),
    ) 
    booking = cursor.fetchone()

    if not booking:
        print("No booking found for that PNR.")
        return

    if booking["status"].lower() == "cancelled":
        print("This ticket is already cancelled.")
        return

    refund_amount = input("Enter refundable amount: ").strip()
    reason = input("Enter cancellation reason: ").strip()

    try:
        cursor.execute(
            """
            UPDATE bookings
            SET status = 'Cancelled'
            WHERE booking_id = %s
            """,
            (booking["booking_id"],),
        )
        cursor.execute(
            """
            INSERT INTO cancellations
            (booking_id, cancel_date, refund_amount, reason)
            VALUES (%s, CURDATE(), %s, %s)
            """,
            (booking["booking_id"], refund_amount, reason),
        )
        cursor.execute(
            """
            UPDATE seats
            SET status = 'Available'
            WHERE schedule_id = %s
              AND status = 'Booked'
            """,
            (booking["schedule_id"],),
        )
        connection.commit()
        print("Ticket cancelled successfully.")
    except db.Error as error:
        connection.rollback()
        print(f"Cancellation failed: {error}")


def view_history(cursor):
    pnr = input("Enter PNR: ").strip().upper()
    cursor.execute(
        """
        SELECT b.booking_id, b.pnr, b.booking_date,
               b.total_amount, b.status,
               t.train_name, t.source, t.destination
        FROM bookings AS b
        JOIN schedules AS s ON s.schedule_id = b.schedule_id
        JOIN trains AS t ON t.train_id = s.train_id
        WHERE b.pnr = %s
        """,
        (pnr,),
    )
    booking = cursor.fetchone()

    if not booking:
        print("No booking found for that PNR.")
        return

    print("\nBooking details:")
    for key, value in booking.items():
        print(f"{key}: {value}")

    cursor.execute(
        """
        SELECT name, age, gender, berth_preference
        FROM passengers
        WHERE booking_id = %s
        """,
        (booking["booking_id"],),
    )
    passengers = cursor.fetchall()

    print("\nPassengers:")
    for passenger in passengers:
        print(
            f"{passenger['name']} | Age: {passenger['age']} | "
            f"Gender: {passenger['gender']} | "
            f"Berth: {passenger['berth_preference']}"
        )


def main():
    connection = connect_database()
    cursor = connection.cursor(dictionary=True)

    try:
        while True:
            print("\n" + "-" * 40)
            print("TRAIN RESERVATION SYSTEM")
            print("-" * 40)
            print("1. Search trains")
            print("2. Book ticket")
            print("3. Cancel ticket")
            print("4. View booking")
            print("5. Exit")

            choice = input("Enter your choice: ").strip()

            if choice == "1":
                search_trains(cursor)
            elif choice == "2":
                book_ticket(cursor, connection)
            elif choice == "3":
                cancel_ticket(cursor, connection)
            elif choice == "4":
                view_history(cursor)
            elif choice == "5":
                print("Thank you!")
                break
            else:
                print("Invalid choice.")
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
