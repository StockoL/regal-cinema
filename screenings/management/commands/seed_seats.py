from django.core.management.base import BaseCommand
from django.db import transaction

from screenings.models import Screen, Seat, SeatingLayout

STALLS = Seat.Area.STALLS
CIRCLE = Seat.Area.CIRCLE

# The plan lives in these constants, so changing it is a one-line edit.

# Circle rows, front to back.
CIRCLE_ROWS = 'ABCDE'
# Circle seat numbers in each row, left to right, one range per block
# with an aisle between blocks: 28 seats a row, 140 in all.
CIRCLE_BLOCKS = [range(28, 19, -1), range(19, 9, -1), range(9, 0, -1)]
# Boxes as (label, column) on a row behind the circle, such as
# [('Box C', 0), ('Box D', 30)]. None for now, so the circle stays at 140.
BOXES = []

# Stalls rows of ten with a centre aisle at column 5.
ROW_COLUMNS = [0, 1, 2, 3, 4, 6, 7, 8, 9, 10]


class Command(BaseCommand):
    help = (
        'Load the demo seat plan for Screen 1: the circle, a Standard '
        'stalls layout and a Tables layout. Demo data for a fictional '
        'venue, so it is run by hand and never by a migration.'
    )

    @transaction.atomic
    def handle(self, *args, **options):
        screen, _ = Screen.objects.get_or_create(name='Screen 1')
        if screen.seats.exists():
            self.stdout.write('Screen 1 already has seats. Nothing changed.')
            return

        standard = SeatingLayout.objects.create(
            screen=screen, name='Standard', is_default=True
        )
        tables = SeatingLayout.objects.create(screen=screen, name='Tables')
        seats = (
            self.circle(screen)
            + self.standard_stalls(screen, standard)
            + self.table_stalls(screen, tables)
        )
        for seat in seats:
            seat.full_clean()
        Seat.objects.bulk_create(seats)
        self.stdout.write(
            f'Screen 1 seeded with {len(seats)} seats. '
            f'Usual capacity is {screen.capacity}.'
        )

    def circle(self, screen):
        """The circle rows and blocks above, then any boxes. Fixed seats,
        so they appear in every layout."""
        seats = []
        for row_index, row_label in enumerate(CIRCLE_ROWS):
            column = 0
            for block in CIRCLE_BLOCKS:
                for number in block:
                    seats.append(Seat(
                        screen=screen, area=CIRCLE, row_label=row_label,
                        number=number, row_index=row_index,
                        column_index=column,
                    ))
                    column += 1
                column += 1
        for number, (name, column) in enumerate(BOXES, start=1):
            seats.append(Seat(
                screen=screen, area=CIRCLE, row_label='Box', number=number,
                row_index=len(CIRCLE_ROWS), column_index=column,
                label_override=name,
            ))
        return seats

    def standard_stalls(self, screen, layout):
        """46 seats in rows. A wheelchair space at each end of the front
        row, with a companion seat beside each."""
        positions = [
            (row, column) for row in range(4) for column in ROW_COLUMNS
        ]
        positions += [(4, column) for column in (0, 1, 2, 8, 9, 10)]
        seats = []
        for number, (row, column) in enumerate(positions, start=1):
            seats.append(Seat(
                screen=screen, layout=layout, area=STALLS, number=number,
                row_index=row, column_index=column,
                is_wheelchair_space=(row == 0 and column in (0, 10)),
                is_companion_seat=(row == 0 and column in (1, 9)),
            ))
        return seats

    def table_stalls(self, screen, layout):
        """Eight tables of four, then a back row with two wheelchair
        spaces and their companion seats."""
        seats, number = [], 1
        for row in range(4):
            for pair, columns in enumerate([(0, 1), (3, 4), (6, 7), (9, 10)]):
                for column in columns:
                    seats.append(Seat(
                        screen=screen, layout=layout, area=STALLS,
                        number=number, row_index=row, column_index=column,
                        table_number=(row // 2) * 4 + pair + 1,
                    ))
                    number += 1
        for column in (0, 1, 9, 10):
            seats.append(Seat(
                screen=screen, layout=layout, area=STALLS, number=number,
                row_index=4, column_index=column,
                is_wheelchair_space=column in (0, 10),
                is_companion_seat=column in (1, 9),
            ))
            number += 1
        return seats
