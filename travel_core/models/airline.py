from odoo import _, api, fields, models


class Airline(models.Model):
    _name = "travel_core.airline"
    _description = "Travel Airline"

    code = fields.Char("Code")
    name = fields.Char("Name", required=True)
    partner_id = fields.Many2one("res.partner", "Contact")
    flight_ids = fields.One2many("travel_core.flight", "airline_id", "Flights")


class Flight(models.Model):
    _name = "travel_core.flight"
    _description = "Travel Flight"

    DAYS_SELECTION = [
        ("0", "Monday"),
        ("1", "Tuesday"),
        ("2", "Wednesday"),
        ("3", "Thursday"),
        ("4", "Friday"),
        ("5", "Saturday"),
        ("6", "Sunday"),
    ]

    airline_id = fields.Many2one("travel_core.airline", "Airline")
    product_id = fields.Many2one("product.product")

    name = fields.Char("Flight Number", required=True)
    active_days = fields.Many2many(
        "travel_core.flight_day_config",
        string="Operating Days",
        help="Days of week when this flight operates",
    )
    departure_time = fields.Float(
        "Departure Time", help="Scheduled departure time (local time)"
    )
    arrival_time = fields.Float(
        "Arrival Time", help="Scheduled arrival time (local time)"
    )
    origin = fields.Many2one("travel_core.destination", "Origin", required=True)
    destination = fields.Many2one(
        "travel_core.destination", "Destination", required=True
    )
    duration = fields.Float("Duration (hours)", compute="_compute_duration", store=True)

    # For specific date overrides
    specific_dates = fields.One2many(
        "travel_core.flight_specific_date",
        "flight_id",
        string="Date Exceptions",
        help="Specific date overrides (holidays, special schedules)",
    )
    origin = fields.Many2one("travel_core.destination", "Origin")
    destination = fields.Many2one("travel_core.destination", "Destination")

    @api.depends("departure_time", "arrival_time")
    def _compute_duration(self):
        for flight in self:
            if flight.departure_time and flight.arrival_time:
                # Handle overnight flights (arrival next day)
                if flight.arrival_time < flight.departure_time:
                    flight.duration = (24 + flight.arrival_time) - flight.departure_time
                else:
                    flight.duration = flight.arrival_time - flight.departure_time
            else:
                flight.duration = 0

    def get_next_flight_date(self, from_date):
        """Get the next occurrence of this flight after the given date"""
        self.ensure_one()
        # TODO: Implement logic to calculate the next flight date based on
        # the active days and the specific dates
        pass


class FlightDayConfig(models.Model):
    _name = "travel_core.flight_day_config"
    _description = "Flight Day Configuration"

    day_of_week = fields.Selection(
        selection=[
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        required=True,
    )
    flight_id = fields.Many2one("travel_core.flight", "Flight")


class FlightSpecificDate(models.Model):
    _name = "travel_core.flight_specific_date"
    _description = "Flight Specific Date Exception"

    flight_id = fields.Many2one("travel_core.flight", "Flight", required=True)
    date = fields.Date("Date", required=True)
    is_cancelled = fields.Boolean("Cancelled")
    special_departure_time = fields.Float("Special Departure Time")
    special_arrival_time = fields.Float("Special Arrival Time")
    reason = fields.Char("Reason")
