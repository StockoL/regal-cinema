/*
 * The seat map's keyboard (architecture 4.17).
 *
 * Without this script every seat is an ordinary checkbox you can tab
 * to. With it, the whole map is one tab stop and the arrow keys move
 * between seats along the grid, skipping aisles, gaps and seats that
 * can't be chosen. A roving tabindex does it: only the seat with focus
 * is in the tab order. Enter chooses a seat as well as Space, because
 * a plain checkbox only answers to Space.
 */
(() => {
  'use strict';

  const map = document.querySelector('[data-seat-map]');
  if (!map) return;

  const seats = [...map.querySelectorAll('.seat__input:not(:disabled)')];
  if (!seats.length) return;

  // Rows run on from the stalls into the circle, so Down from the back
  // of the stalls reaches the front of the circle.
  const areaOrder = ['stalls', 'circle'];
  const place = (seat) => ({
    row: areaOrder.indexOf(seat.dataset.area) * 1000 + Number(seat.dataset.row),
    col: Number(seat.dataset.col),
  });

  function makeCurrent(seat) {
    seats.forEach((other) => { other.tabIndex = -1; });
    seat.tabIndex = 0;
  }

  function moveTo(seat) {
    if (!seat) return;
    makeCurrent(seat);
    seat.focus();
    seat.closest('.seat').scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }

  // The nearest seat along the row, in the direction asked.
  function along(from, step) {
    const here = place(from);
    return seats
      .filter((seat) => place(seat).row === here.row)
      .filter((seat) => Math.sign(place(seat).col - here.col) === step)
      .sort((a, b) => Math.abs(place(a).col - here.col) - Math.abs(place(b).col - here.col))[0];
  }

  // The seat closest in column in the nearest row in front or behind.
  function across(from, step) {
    const here = place(from);
    const rows = [...new Set(seats.map((seat) => place(seat).row))]
      .filter((row) => Math.sign(row - here.row) === step)
      .sort((a, b) => Math.abs(a - here.row) - Math.abs(b - here.row));
    if (!rows.length) return null;
    return seats
      .filter((seat) => place(seat).row === rows[0])
      .sort((a, b) => Math.abs(place(a).col - here.col) - Math.abs(place(b).col - here.col))[0];
  }

  function rowEnd(from, step) {
    const row = seats.filter((seat) => place(seat).row === place(from).row);
    return step < 0 ? row[0] : row[row.length - 1];
  }

  makeCurrent(seats.find((seat) => seat.checked) || seats[0]);

  map.addEventListener('focusin', (event) => {
    if (seats.includes(event.target)) makeCurrent(event.target);
  });

  map.addEventListener('keydown', (event) => {
    const seat = event.target;
    if (!seats.includes(seat)) return;
    const moves = {
      ArrowLeft: () => along(seat, -1),
      ArrowRight: () => along(seat, 1),
      ArrowUp: () => across(seat, -1),
      ArrowDown: () => across(seat, 1),
      Home: () => rowEnd(seat, -1),
      End: () => rowEnd(seat, 1),
    };
    if (moves[event.key]) {
      event.preventDefault();
      moveTo(moves[event.key]());
    } else if (event.key === 'Enter') {
      // Choose the seat rather than submit the form.
      event.preventDefault();
      seat.click();
    }
  });
})();
