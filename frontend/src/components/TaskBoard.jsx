import React from "react";

export function TaskBoard({ bookings }) {
  const items = [...(bookings || [])].sort((left, right) => left.check_in.localeCompare(right.check_in));

  if (!items.length) {
    return <div className="empty-board">Пока нет подтвержденных бронирований по выбранному владельцу.</div>;
  }

  return (
    <section className="route-lane">
      {items.slice(0, 6).map((booking) => (
        <article className="route-stop" key={booking.booking_id}>
          <p className="lesson-type">Booking {booking.booking_id.slice(0, 8)}</p>
          <h4>
            {booking.check_in} → {booking.check_out}
          </h4>
          <div className="lesson-meta">
            <span>{booking.listing_id}</span>
            <span>{booking.status}</span>
          </div>
        </article>
      ))}
    </section>
  );
}
