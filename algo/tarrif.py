from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Literal
import math

app = FastAPI(title="Airport Handling Cost Engine")

# -----------------------------
# 1) Tariff datastore (seeded with real items & sources)
# -----------------------------
TARIFFS = {
    "DELHI IGI": {
        "currency": "INR",
        "landing": {
            # Domestic: ₹441/MT, min ₹5,788
            "domestic_per_mt": 441.0,
            "domestic_min": 5788.0,
            # International slabbed rate (in INR) per MT
            "intl_slabs": [
                {"max_mt": 100, "per_mt": 662.0},   # up to 100 MT
                {"max_mt": None, "per_mt": 772.0}, # >100 MT
            ],
            "intl_min_usd": 128.0,  # keep for reference if you invoice in USD
        },
        "parking": {
            # Domestic per-hour per MT
            "domestic_per_mt_per_hr": 18.22,
            # Free parking rule (2h free + 15 min buffer)
            "free_hours": 2.0,
            "free_buffer_minutes": 15,
            # If you need intl parking, add per-hr slabs here similar to landing
        },
        "udf": {  # example UDF schedule (use only if applicable at IGI)
            "domestic_depart": 1050.0,
            "domestic_arrive": 450.0,
            "intl_depart": 1540.0,
            "intl_arrive": 660.0,
        },
        "atc_navigation_flat": 0.0,  # set if applicable
    },

    "HYDERABAD RGIA": {
        "currency": "INR",
        "landing": {
            # Use your known per-MT rates + a minimum per schedule
            "domestic_per_mt": 0.0,        # fill from current card if needed
            "domestic_min": 4000.0,        # published minimum
            # Add intl slabs when you add intl rates
            "intl_slabs": [],
            "intl_min_usd": None,
        },
        "parking": {
            "domestic_per_mt_per_hr": 0.0, # fill from schedule if needed
            "free_hours": 0.0,
            "free_buffer_minutes": 0,
        },
        "udf": None,
        "atc_navigation_flat": 0.0,
    },
}

# -----------------------------
# 2) Request models
# -----------------------------
class AirportStop(BaseModel):
    airport: str = Field(..., description="Airport name key, e.g. 'DELHI IGI'")
    leg_type: Literal["domestic", "international"]
    mtow_kg: float = Field(..., gt=0, description="Aircraft MTOW in kilograms")
    parking_hours: float = Field(0, ge=0, description="Gate/stand time to bill")
    pax_departing: int = 0
    pax_arriving: int = 0

class RouteQuote(BaseModel):
    stops: List[AirportStop]
    flight_hours: float = Field(..., ge=0)
    hourly_rate: float = Field(..., ge=0)

# Update the RouteQuote model to include multiple routes
class MultiRouteQuote(BaseModel):
    routes: List[RouteQuote]

# -----------------------------
# 3) Helpers
# -----------------------------
def nearest_mt(mtow_kg: float) -> int:
    # AERA: charges based on nearest MT (i.e., 1000 kg) for many airports
    return int(round(mtow_kg / 1000.0))

def parking_billable_hours(raw_hours: float, free_hours: float, buffer_min: int) -> float:
    # Apply free window + buffer
    effective_free = free_hours + (buffer_min / 60.0)
    return max(0.0, raw_hours - effective_free)

def rate_for_intl_slab(slabs, weight_mt: int) -> float:
    for s in slabs:
        if s["max_mt"] is None or weight_mt <= s["max_mt"]:
            return s["per_mt"]
    return 0.0

# -----------------------------
# 4) Core cost engine
# -----------------------------
@app.post("/estimate-cost")
def estimate_cost(route: RouteQuote):
    total_handling = 0.0
    breakdown = []

    for stop in route.stops:
        rules = TARIFFS.get(stop.airport.upper())
        if not rules:
            raise ValueError(f"No tariff configured for airport: {stop.airport}")

        wt_mt = nearest_mt(stop.mtow_kg)

        # Landing
        if stop.leg_type == "domestic":
            landing_raw = wt_mt * rules["landing"]["domestic_per_mt"]
            landing_fee = max(landing_raw, rules["landing"]["domestic_min"])
        else:  # international
            per_mt = rate_for_intl_slab(rules["landing"]["intl_slabs"], wt_mt)
            landing_fee = wt_mt * per_mt
            # (Optional) if you invoice in USD minimum, convert; else keep INR min per airport card.

        # Parking
        pk_conf = rules["parking"]
        billable_hrs = parking_billable_hours(stop.parking_hours, pk_conf["free_hours"], pk_conf["free_buffer_minutes"])
        parking_fee = wt_mt * pk_conf["domestic_per_mt_per_hr"] * billable_hrs  # adjust if intl differs

        # UDF (per passenger) — use only if defined/applicable at that airport
        udf_fee = 0.0
        udf = rules.get("udf")
        if udf:
            if stop.leg_type == "domestic":
                udf_fee += stop.pax_departing * udf["domestic_depart"]
                udf_fee += stop.pax_arriving  * udf["domestic_arrive"]
            else:
                udf_fee += stop.pax_departing * udf["intl_depart"]
                udf_fee += stop.pax_arriving  * udf["intl_arrive"]

        # ATC/Navigation (flat)
        atc_fee = rules.get("atc_navigation_flat", 0.0)

        airport_total = landing_fee + parking_fee + udf_fee + atc_fee
        total_handling += airport_total

        breakdown.append({
            "airport": stop.airport,
            "leg_type": stop.leg_type,
            "weight_mt_billed": wt_mt,
            "landing_fee": landing_fee,
            "parking_fee": parking_fee,
            "udf_fee": udf_fee,
            "atc_fee": atc_fee,
            "total_airport": airport_total,
        })

    # Flight cost
    flight_cost = route.flight_hours * route.hourly_rate

    # Subtotal & taxes
    subtotal = total_handling + flight_cost
    gst = subtotal * 0.18

    # Your requested uplift
    extra_charge = 15000.0
    final_cost = subtotal + gst + extra_charge

    return {
        "currency": "INR",
        "breakdown": breakdown,
        "total_handling_charges": total_handling,
        "flight_cost": flight_cost,
        "subtotal": subtotal,
        "gst_18_percent": gst,
        "extra_charge": extra_charge,
        "final_estimated_cost": final_cost
    }

# Add a new endpoint for multiway trip cost estimation
@app.post("/estimate-multiway-cost")
def estimate_multiway_cost(multi_route: MultiRouteQuote):
    total_handling = 0.0
    total_flight_cost = 0.0
    combined_breakdown = []

    for route in multi_route.routes:
        for stop in route.stops:
            rules = TARIFFS.get(stop.airport.upper())
            if not rules:
                raise ValueError(f"No tariff configured for airport: {stop.airport}")

            wt_mt = nearest_mt(stop.mtow_kg)

            # Landing
            if stop.leg_type == "domestic":
                landing_raw = wt_mt * rules["landing"]["domestic_per_mt"]
                landing_fee = max(landing_raw, rules["landing"]["domestic_min"])
            else:  # international
                per_mt = rate_for_intl_slab(rules["landing"]["intl_slabs"], wt_mt)
                landing_fee = wt_mt * per_mt

            # Parking
            pk_conf = rules["parking"]
            billable_hrs = parking_billable_hours(stop.parking_hours, pk_conf["free_hours"], pk_conf["free_buffer_minutes"])
            parking_fee = wt_mt * pk_conf["domestic_per_mt_per_hr"] * billable_hrs

            # UDF (per passenger) — use only if defined/applicable at that airport
            udf_fee = 0.0
            udf = rules.get("udf")
            if udf:
                if stop.leg_type == "domestic":
                    udf_fee += stop.pax_departing * udf["domestic_depart"]
                    udf_fee += stop.pax_arriving  * udf["domestic_arrive"]
                else:
                    udf_fee += stop.pax_departing * udf["intl_depart"]
                    udf_fee += stop.pax_arriving  * udf["intl_arrive"]

            # ATC/Navigation (flat)
            atc_fee = rules.get("atc_navigation_flat", 0.0)

            airport_total = landing_fee + parking_fee + udf_fee + atc_fee
            total_handling += airport_total

            combined_breakdown.append({
                "airport": stop.airport,
                "leg_type": stop.leg_type,
                "weight_mt_billed": wt_mt,
                "landing_fee": landing_fee,
                "parking_fee": parking_fee,
                "udf_fee": udf_fee,
                "atc_fee": atc_fee,
                "total_airport": airport_total,
            })

        # Add flight cost for the route
        total_flight_cost += route.flight_hours * route.hourly_rate

    # Subtotal & taxes
    subtotal = total_handling + total_flight_cost
    gst = subtotal * 0.18

    # Your requested uplift
    extra_charge = 15000.0
    final_cost = subtotal + gst + extra_charge

    return {
        "currency": "INR",
        "breakdown": combined_breakdown,
        "total_handling_charges": total_handling,
        "total_flight_cost": total_flight_cost,
        "subtotal": subtotal,
        "gst_18_percent": gst,
        "extra_charge": extra_charge,
        "final_estimated_cost": final_cost
    }
